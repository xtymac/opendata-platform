import asyncio
import csv
import io
import json
import logging
import os
import re
from typing import Iterable, List, Literal, Optional
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from openai import OpenAI
from langdetect import DetectorFactory, LangDetectException, detect

from .tools import (
    read_server_file as ssh_read_file,
    configure_ssh_logger,
    fetch_resource,
    configure_resource_logger,
)

logger = logging.getLogger("ckan_assistant")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

CKAN_BASE_URL = os.getenv("CKAN_BASE_URL", "http://ckan:5000")
CKAN_SITE_URL = os.getenv("CKAN_SITE_URL", CKAN_BASE_URL)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

configure_ssh_logger(logger)
configure_resource_logger(logger)

DetectorFactory.seed = 0

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{2,}")
PAREN_CONTENT_RE = re.compile(r"[\(（]([^()（）]{1,40})[\)）]")
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "data",
    "dataset",
    "datasets",
    "information",
    "about",
    "search",
    "find",
    "show",
    "please",
    "help",
    "are",
    "any",
    "what",
    "which",
    "have",
    "has",
    "latest",
    "recent",
}

RESOURCE_RE = re.compile(r"resource/([0-9a-fA-F-]{36})")
UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
FILE_PATH_RE = re.compile(r"/(?:var|etc|srv|home)/[\w\-./]+")

app = FastAPI(title="CKAN Assistant Service", version="0.1.0")


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: List[HistoryMessage] = []
    language: Optional[str] = Field(None, description="Preferred response language code if provided")


class ChatResponse(BaseModel):
    reply: str
    context: Optional[str] = None
    sources: List[str] = []


def _extract_keywords(text: str) -> List[str]:
    tokens = [match.lower() for match in WORD_RE.findall(text or "")]
    keywords: List[str] = []
    for token in tokens:
        if token in STOPWORDS:
            continue
        keywords.append(token)

    for inner in PAREN_CONTENT_RE.findall(text or ""):
        for token in WORD_RE.findall(inner):
            lowered = token.lower()
            if lowered in STOPWORDS:
                continue
            keywords.append(lowered)

    deduped: List[str] = []
    seen: set[str] = set()
    for token in keywords:
        if token not in seen:
            seen.add(token)
            deduped.append(token)
    return deduped


def _requires_translation(text: str, extracted_keywords: Iterable[str]) -> bool:
    if not text:
        return False
    if any(ord(char) > 127 for char in text) and not any(
        keyword.isalpha() and keyword.isascii() for keyword in extracted_keywords
    ):
        return True
    return False


def _extract_resource_ids(text: str) -> List[str]:
    if not text:
        return []
    matches = RESOURCE_RE.findall(text)
    if matches:
        unique = list(dict.fromkeys(matches))
        logger.debug("Resource pattern matches: %s", unique)
        return unique
    matches = UUID_RE.findall(text)
    unique = list(dict.fromkeys(matches))
    if unique:
        logger.debug("UUID pattern matches: %s", unique)
    return unique


def _should_enable_file_tool(text: Optional[str]) -> bool:
    if not text:
        return False
    lowered = text.lower()
    file_keywords = [
        "/var/log",
        "/etc/",
        "tail ",
        "查看日志",
        "read log",
        "error log",
        "log file",
        "读取",
    ]
    if any(keyword in lowered for keyword in file_keywords):
        return True
    return FILE_PATH_RE.search(text) is not None


def _indent_block(text: str, prefix: str = "    ") -> str:
    return "\n".join(f"{prefix}{line}" for line in text.splitlines())


def _is_csv_resource(resource: dict) -> bool:
    fmt = (resource.get("format") or "").lower()
    mimetype = (resource.get("mimetype") or "").lower()
    if fmt == "csv" or mimetype == "text/csv":
        return True

    url = resource.get("url") or ""
    if not url:
        return False

    try:
        path = urlparse(url).path.lower()
    except Exception:  # noqa: BLE001
        return False
    return path.endswith(".csv")


def _format_preview_table(columns: List[str], rows: List[List[str]], shown_rows: int) -> str:
    visible_columns = columns[:8]
    formatted_rows = [" | ".join(visible_columns)]

    for row in rows[:shown_rows]:
        values = []
        for column, cell in zip(visible_columns, row + [""] * len(visible_columns)):
            text = str(cell) if cell is not None else ""
            if len(text) > 80:
                text = text[:77] + "..."
            values.append(text)
        formatted_rows.append(" | ".join(values))

    if len(columns) > len(visible_columns):
        hidden = len(columns) - len(visible_columns)
        formatted_rows.append(f"(... {hidden} more columns hidden)")

    if len(rows) > shown_rows:
        extra = len(rows) - shown_rows
        formatted_rows.append(f"(+{extra} additional rows not shown)")

    return "\n".join(formatted_rows)


async def _fetch_datastore_preview(resource_id: str, limit: int = 5) -> Optional[str]:
    if not resource_id:
        return None

    search_url = f"{CKAN_BASE_URL.rstrip('/')}/api/3/action/datastore_search"
    params = {"resource_id": resource_id, "limit": limit}

    try:
        async with httpx.AsyncClient(timeout=5.0) as session:
            response = await session.get(search_url, params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:  # noqa: BLE001
        logger.debug("datastore_search failed for %s: %s", resource_id, exc)
        return None

    if not payload.get("success"):
        return None

    result = payload.get("result") or {}
    records = result.get("records") or []
    fields = result.get("fields") or []

    if not records:
        return None

    columns = [field.get("id") for field in fields if field.get("id")]
    if not columns:
        columns = list(records[0].keys())

    table_rows: List[List[str]] = []
    for record in records[:limit]:
        row = [record.get(column, "") for column in columns]
        table_rows.append(["" if value is None else value for value in row])

    preview = _format_preview_table(columns, table_rows, limit)
    return "Datastore preview (first {rows} rows):\n{table}".format(
        rows=min(limit, len(table_rows)),
        table=preview,
    )


async def _fetch_csv_preview_from_url(resource: dict, limit: int = 5) -> Optional[str]:
    url = resource.get("url")
    if not url:
        return None

    max_bytes = 200_000
    newline_target = limit + 6
    chunks: List[bytes] = []
    collected = 0

    try:
        async with httpx.AsyncClient(timeout=10.0) as session:
            async with session.stream("GET", url, headers={"Range": "bytes=0-65535"}) as response:
                response.raise_for_status()
                encoding = response.charset_encoding or response.encoding or "utf-8"
                newlines = 0
                async for chunk in response.aiter_bytes():
                    chunks.append(chunk)
                    collected += len(chunk)
                    newlines += chunk.count(b"\n")
                    if collected >= max_bytes or newlines >= newline_target:
                        break
    except Exception as exc:  # noqa: BLE001
        logger.debug("CSV preview download failed for %s: %s", url, exc)
        return None

    if not chunks:
        return None

    raw = b"".join(chunks)
    try:
        text = raw.decode(encoding, errors="ignore")
    except Exception:  # noqa: BLE001
        text = raw.decode("utf-8", errors="ignore")

    reader = csv.reader(io.StringIO(text))
    rows: List[List[str]] = []
    try:
        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue
            rows.append(row)
            if len(rows) >= limit + 1:
                break
    except Exception as exc:  # noqa: BLE001
        logger.debug("CSV parsing failed for %s: %s", url, exc)
        return None

    if not rows:
        return None

    header = rows[0]
    data_rows = rows[1:] or []
    if not data_rows:
        return None

    preview = _format_preview_table(header, data_rows, min(limit, len(data_rows)))
    return "CSV file preview (first {rows} rows):\n{table}".format(
        rows=min(limit, len(data_rows)),
        table=preview,
    )


async def _build_csv_preview(resource: dict, limit: int = 5) -> Optional[str]:
    if not _is_csv_resource(resource):
        return None

    resource_id = resource.get("id")
    if resource.get("datastore_active"):
        preview = await _fetch_datastore_preview(resource_id, limit)
        if preview:
            return preview

    preview = await _fetch_csv_preview_from_url(resource, limit)
    return preview


def _summarise_resource(resource: dict) -> tuple[str, Optional[str], List[str]]:
    name = resource.get("name") or resource.get("title") or "Unnamed resource"
    fmt = resource.get("format") or resource.get("mimetype") or "Unknown format"
    datastore = resource.get("datastore_active")
    url = resource.get("url")
    package_id = resource.get("package_id")
    rid = resource.get("id")

    status = "enabled" if datastore else "not enabled"
    size = resource.get("size")
    last_modified = resource.get("last_modified")

    summary = [
        f"- {name} ({fmt})",
        f"  datastore_active: {status}",
    ]
    if size:
        summary.append(f"  size: {size}")
    if last_modified:
        summary.append(f"  last_modified: {last_modified}")
    if url:
        summary.append(f"  source_url: {url}")

    hints: List[str] = []
    if fmt and fmt.lower() == "csv" and not datastore:
        note = "CSV previews require DataStore ingest (run DataPusher or enable datastore for this resource)."
        summary.append(f"  note: {note}")
        hints.append(note)
    elif not datastore:
        note = "Previews are disabled because DataStore is not enabled for this resource."
        summary.append(f"  note: {note}")
        hints.append(note)
    elif datastore:
        hints.append("DataStore is active; if preview fails, check the datastore table and recent DataPusher jobs.")

    resource_url = None
    if package_id and rid:
        resource_url = f"{CKAN_SITE_URL.rstrip('/')}/dataset/{package_id}/resource/{rid}"

    return "\n".join(summary), resource_url, hints


async def translate_to_english(text: str) -> Optional[str]:
    if not client or not text:
        return None

    try:
        language = detect(text)
    except LangDetectException:
        language = "unknown"

    if language in {"en", "unknown"}:
        return None

    def _perform_translation() -> Optional[str]:
        try:
            completion = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Translate the user's query into concise English dataset search keywords. "
                            "Respond with a short comma-separated list of keywords only."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                temperature=0,
                max_tokens=60,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAI translation failed: %s", exc)
            return None

        choice = completion.choices[0]
        if not choice.message or not choice.message.content:
            return None
        return choice.message.content.strip()

    translated = await asyncio.to_thread(_perform_translation)
    return translated


async def build_search_queries(raw_query: str) -> List[str]:
    base = (raw_query or "").strip()
    keywords = _extract_keywords(base)
    queries: List[str] = []

    def _append(items: Iterable[str]) -> None:
        for item in items:
            cleaned = (item or "").strip()
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered not in {q.lower() for q in queries}:
                queries.append(cleaned)

    if base:
        _append([base])
    if keywords:
        _append([" ".join(keywords)])
        _append(keywords)

    if _requires_translation(base, keywords):
        translated = await translate_to_english(base)
        if translated:
            translated_keywords = [segment.strip() for segment in re.split(r"[,/;]\s*", translated) if segment.strip()]
            _append([translated])
            if translated_keywords:
                _append(translated_keywords)

    return queries[:6]


async def fetch_ckan_context(query: str, rows: int = 3) -> tuple[str, List[str]]:
    """Query CKAN for datasets matching the user prompt using multiple strategies."""

    search_variants = await build_search_queries(query)
    if not search_variants:
        return "", []

    search_url = f"{CKAN_BASE_URL.rstrip('/')}/api/3/action/package_search"
    sources: List[str] = []
    summaries: List[str] = []
    seen_ids: set[str] = set()

    try:
        async with httpx.AsyncClient(timeout=5.0) as session:
            for variant in search_variants:
                params = {"q": variant, "rows": rows}
                try:
                    response = await session.get(search_url, params=params)
                    response.raise_for_status()
                except Exception as exc:  # noqa: BLE001
                    logger.debug("CKAN search request failed for '%s': %s", variant, exc)
                    continue

                payload = response.json()
                if not payload.get("success"):
                    continue

                results = payload.get("result", {}).get("results", [])
                for dataset in results:
                    dataset_id = dataset.get("id")
                    if not dataset_id or dataset_id in seen_ids:
                        continue
                    seen_ids.add(dataset_id)

                    title = dataset.get("title") or dataset.get("name")
                    name = dataset.get("name")
                    notes = (dataset.get("notes") or "").strip()
                    if notes:
                        notes = notes.replace("\n", " ")
                    dataset_url = f"{CKAN_SITE_URL.rstrip('/')}/dataset/{name}" if name else ""
                    summary = f"- {title} ({name})" if name else f"- {title}"
                    if notes:
                        summary += f"\n  摘要: {notes[:400]}"
                    if dataset_url:
                        summary += f"\n  网址: {dataset_url}"
                        sources.append(dataset_url)
                    summaries.append(summary)

                if len(seen_ids) >= rows:
                    break
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch CKAN context: %s", exc)
        return "", sources

    context_text = "\n".join(summaries)
    return context_text, sources


async def generate_response(messages: List[dict], allow_file_tool: bool) -> str:
    if not client:
        raise HTTPException(status_code=500, detail="OpenAI client not configured")

    tool_definitions: List[dict] = []
    if allow_file_tool:
        tool_definitions.append(
            {
                "type": "function",
                "function": {
                    "name": "read_server_file",
                    "description": "Read a file from the CKAN server over the read-only SSH bridge. Only retrieve relevant log or config snippets.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Absolute file path within permitted directories.",
                            },
                            "tail_lines": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 500,
                                "description": "Optional number of trailing lines to fetch.",
                            },
                        },
                        "required": ["path"],
                    },
                },
            }
        )

    conversation: List[dict] = list(messages)
    tool_messages: List[dict] = []

    while True:
        try:
            completion = await asyncio.to_thread(
                client.chat.completions.create,
                model=OPENAI_MODEL,
                messages=conversation + tool_messages,
                temperature=0.2,
                tools=tool_definitions or None,
                tool_choice="auto" if tool_definitions else None,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("OpenAI completion failed: %s", exc)
            raise HTTPException(status_code=502, detail="Assistant model unavailable") from exc

        choice = completion.choices[0]
        message = choice.message

        if not message:
            return ""

        tool_calls = message.tool_calls or []

        if not tool_calls:
            return (message.content or "").strip()

        conversation.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": call.type,
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ],
            }
        )

        tool_messages = []

        for call in tool_calls:
            name = call.function.name
            arguments = call.function.arguments or "{}"
            try:
                params = json.loads(arguments)
            except json.JSONDecodeError as exc:
                logger.warning("Invalid arguments for tool %s: %s", name, exc)
                params = {}

            if name == "read_server_file" and allow_file_tool:
                try:
                    output = await ssh_read_file(**params)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("read_server_file failed: %s", exc)
                    output = json.dumps({"error": str(exc)})
            else:
                output = json.dumps({"error": f"Unknown tool {name}"})

            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": output,
                }
            )


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Primary chat endpoint for the CKAN assistant."""
    logger.info("Received assistant query: %s", request.message[:80])
    logger.info("Raw message repr: %r", request.message)

    resource_summaries: List[str] = []
    resource_hints: List[str] = []
    resource_ids = _extract_resource_ids(request.message)
    if not resource_ids:
        for item in reversed(request.history):
            if item.role != "user":
                continue
            resource_ids = _extract_resource_ids(item.content)
            if resource_ids:
                break

    allow_file_tool = _should_enable_file_tool(request.message)
    if not allow_file_tool:
        for item in reversed(request.history):
            if item.role != "user":
                continue
            if _should_enable_file_tool(item.content):
                allow_file_tool = True
                break
    logger.info("allow_file_tool evaluated to %s", allow_file_tool)

    context_text = ""
    sources: List[str] = []
    if resource_ids:
        logger.debug("Detected resource IDs in query: %s", resource_ids)
    else:
        context_text, sources = await fetch_ckan_context(request.message)

    for resource_id in resource_ids[:3]:
        try:
            resource = await fetch_resource(resource_id)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Unable to fetch resource %s: %s", resource_id, exc)
            continue

        summary, resource_url, hints = _summarise_resource(resource)
        preview = await _build_csv_preview(resource)
        if preview:
            summary = summary + "\n  CSV preview:\n" + _indent_block(preview)

        resource_summaries.append(summary)
        resource_hints.extend(hints)
        if resource_url:
            sources.append(resource_url)
        direct_url = resource.get("url")
        if direct_url:
            sources.append(direct_url)

    system_prompt = (
        "You are an AI assistant for a CKAN open data portal."
        " Provide helpful answers based on CKAN datasets, configuration, and troubleshooting knowledge."
        " Prefer concise answers with bullet points when listing items."
        " If you suggest datasets, include their titles and URLs when available."
        " When resource metadata is provided, trust it (especially datastore_active, format, source_url) before forming conclusions."
        " Do not assume files are missing unless metadata or authorised tool output explicitly shows that."
        " Only request server log snippets when the user clearly asks for logs or file contents."
    )

    if request.language:
        system_prompt += f" Respond in {request.language}."

    conversation: List[dict] = [
        {"role": "system", "content": system_prompt},
    ]

    for item in request.history:
        conversation.append({"role": item.role, "content": item.content})

    if resource_summaries:
        conversation.append(
            {
                "role": "system",
                "content": "Resource metadata summary:\n" + "\n".join(resource_summaries),
            }
        )

    if resource_hints:
        conversation.append(
            {
                "role": "system",
                "content": "Resource diagnostics hints:\n" + "\n".join(dict.fromkeys(resource_hints)),
            }
        )

    user_message = request.message
    if context_text:
        user_message += "\n\nRelevant CKAN datasets:\n" + context_text
    elif not resource_ids:
        user_message += "\n\nNo relevant CKAN datasets were found automatically."

    conversation.append({"role": "user", "content": user_message})

    reply = await generate_response(conversation, allow_file_tool)

    combined_context = []
    if context_text:
        combined_context.append(context_text)
    if resource_summaries:
        combined_context.extend(resource_summaries)
    if resource_hints:
        combined_context.append("Resource hints:\n" + "\n".join(dict.fromkeys(resource_hints)))

    context_blob = "\n\n".join(combined_context) if combined_context else None

    return ChatResponse(reply=reply, context=context_blob, sources=list(dict.fromkeys(sources)))
