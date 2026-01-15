"""Read-only SSH helper integration."""

from __future__ import annotations

import asyncio
import json
import os
import shlex
from pathlib import PurePosixPath
from typing import Optional

logger = None  # will be assigned from main via init

DEFAULT_ALLOWED = "/var/log:/etc:/srv/app:/home/ubuntu"
MAX_BYTES = 16000


def configure_logger(shared_logger) -> None:
    global logger
    logger = shared_logger


def _allowed_roots() -> list[str]:
    raw = os.getenv("SSH_ASSISTANT_ALLOWED_ROOTS", DEFAULT_ALLOWED)
    return [path.strip() for path in raw.split(":") if path.strip()]


def _sanitize_path(path: str) -> str:
    if not path:
        raise ValueError("path is required")

    pure = PurePosixPath(path)
    normalized = "/" + str(pure).lstrip("/")
    for root in _allowed_roots():
        if normalized.startswith(root.rstrip("/") + "/") or normalized == root.rstrip("/"):
            return normalized
    raise ValueError("path is outside allowed roots")


async def _run_subprocess(cmd: list[str]) -> tuple[str, str, int]:
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return stdout.decode("utf-8", "replace"), stderr.decode("utf-8", "replace"), process.returncode


async def read_server_file(*, path: str, tail_lines: Optional[int] = None) -> str:
    """Call the external read-only SSH tool to fetch file contents."""

    sanitized = _sanitize_path(path)

    base_cmd = os.getenv("SSH_ASSISTANT_TOOL")
    if base_cmd:
        cmd = shlex.split(base_cmd)
        cmd.extend(["--path", sanitized])
        if tail_lines:
            cmd.extend(["--tail", str(max(1, min(int(tail_lines), 500)))])
    else:
        # fallback: read directly from local filesystem
        cmd = []

    if cmd:
        stdout, stderr, code = await _run_subprocess(cmd)
        if code != 0:
            message = f"SSH tool error (code {code}): {stderr.strip() or stdout.strip()}"
            logger.warning("SSH tool failed for %s: %s", sanitized, message)
            raise RuntimeError(message)
        content = stdout
    else:
        # local fallback
        try:
            with open(sanitized, "r", encoding="utf-8", errors="ignore") as handle:
                content = handle.read(MAX_BYTES)
        except OSError as exc:  # pragma: no cover - simple fallback
            raise RuntimeError(str(exc)) from exc

    if len(content) > MAX_BYTES:
        content = content[:MAX_BYTES] + "\n... (truncated)"

    payload = {
        "path": sanitized,
        "tail_lines": tail_lines,
        "content": content,
    }
    return json.dumps(payload, ensure_ascii=False)
