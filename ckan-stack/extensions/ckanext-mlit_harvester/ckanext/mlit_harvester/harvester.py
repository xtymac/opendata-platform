# -*- coding: utf-8 -*-

"""Harvest implementation for the Japan MLIT Data platform."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin

import requests
from requests import RequestException, Response, Session

from ckantoolkit import config as toolkit_config

from ckanext.harvest.harvesters.base import HarvesterBase
from ckanext.harvest.model import HarvestObject

log = logging.getLogger(__name__)

DEFAULT_API_BASE = "https://api.mlit-data.jp"
DEFAULT_SEARCH_PATH = "datasets"
DEFAULT_DATASET_PATH = "datasets"
DEFAULT_DETAIL_TEMPLATE = "{datasets_path}/{guid}"
DEFAULT_DETAIL_RESULT_PATH = None
DEFAULT_API_KEY_HEADER = "X-API-KEY"
DEFAULT_HTTP_METHOD = "GET"
REQUEST_TIMEOUT = 30  # seconds


class MLITHarvester(HarvesterBase):
    """Custom harvester tailored for the MLIT Data platform."""

    def info(self) -> Dict[str, str]:
        return {
            "name": "mlit",
            "title": "MLIT Data Harvester",
            "description": "Harvest datasets from the MLIT Data Platform (Japan MLIT).",
        }

    # ------------------------------------------------------------------
    # Gather stage
    # ------------------------------------------------------------------
    def gather_stage(self, harvest_job) -> List[str]:
        log.info("Starting MLIT gather stage (source=%s)", harvest_job.source.url)

        try:
            config = self._load_config(harvest_job.source.config)
        except ValueError as err:
            message = f"Failed to parse harvest source config: {err}"
            log.error(message)
            self._save_gather_error(message, harvest_job)
            return []

        session = self._get_http_session(config)
        dataset_endpoint = self._build_endpoint(config, config.get("search_path", config["datasets_path"]))

        if not dataset_endpoint:
            message = "Dataset listing endpoint could not be constructed."
            log.error(message)
            self._save_gather_error(message, harvest_job)
            return []

        page_size = config["page_size"]
        page = 1
        seen_remote_ids: set[str] = set()
        object_ids: List[str] = []

        while True:
            params = self._listing_params(config, page=page)
            payload = self._build_search_payload(config, page)
            try:
                response_data = self._send_request(
                    session,
                    dataset_endpoint,
                    params=params,
                    json_payload=payload,
                    method=config.get("http_method", DEFAULT_HTTP_METHOD),
                )
            except Exception as err:  # noqa: BLE001 - propagate detailed error via harvest log
                message = f"Failed to fetch dataset list (page={page}): {err}"
                log.exception(message)
                self._save_gather_error(message, harvest_job)
                return object_ids

            datasets = self._extract_dataset_entries(response_data, config)

            if not datasets:
                log.info("No datasets returned for page %s; stopping pagination", page)
                break

            for dataset in datasets:
                remote_id = self._extract_dataset_guid(dataset, config)
                if not remote_id:
                    log.warning(
                        "Skipped dataset without stable identifier on page %s: %r",
                        page,
                        dataset,
                    )
                    continue

                if remote_id in seen_remote_ids:
                    log.debug("Skipping duplicate dataset id %s", remote_id)
                    continue

                harvest_object = HarvestObject(guid=remote_id, job=harvest_job)
                harvest_object.save()
                object_ids.append(harvest_object.id)
                seen_remote_ids.add(remote_id)

            if len(datasets) < page_size:
                log.info("Reached final page (page=%s)", page)
                break

            page += 1

        return object_ids

    # ------------------------------------------------------------------
    # Fetch stage
    # ------------------------------------------------------------------
    def fetch_stage(self, harvest_object) -> bool:
        log.info("Fetching MLIT dataset (guid=%s)", harvest_object.guid)

        try:
            config = self._load_config(harvest_object.source.config)
        except ValueError as err:
            message = f"Failed to parse harvest source config: {err}"
            log.error(message)
            self._save_object_error(message, harvest_object, "Fetch")
            return False

        session = self._get_http_session(config)
        detail_template = config["detail_path_template"]
        detail_path = detail_template.format(
            guid=quote(harvest_object.guid, safe=""),
            datasets_path=config["datasets_path"],
        )
        detail_endpoint = self._build_endpoint(config, detail_path)

        if not detail_endpoint:
            message = "Dataset detail endpoint could not be constructed."
            log.error(message)
            self._save_object_error(message, harvest_object, "Fetch")
            return False

        try:
            detail_payload = self._build_detail_payload(config, harvest_object.guid)
            dataset_detail = self._send_request(
                session,
                detail_endpoint,
                params=self._detail_params(config),
                json_payload=detail_payload,
                method=config.get("detail_http_method", config.get("http_method", DEFAULT_HTTP_METHOD)),
            )
        except Exception as err:  # noqa: BLE001
            message = f"Failed to fetch dataset {harvest_object.guid}: {err}"
            log.exception(message)
            self._save_object_error(message, harvest_object, "Fetch")
            return False

        detail_result = self._pluck(dataset_detail, config.get("detail_result_path"))
        if detail_result is None:
            detail_result = dataset_detail
        if not isinstance(detail_result, dict):
            message = (
                "Detail response did not yield a JSON object. Adjust 'detail_result_path' "
                "in the harvest source configuration."
            )
            log.error(message)
            self._save_object_error(message, harvest_object, "Fetch")
            return False

        harvest_object.content = json.dumps(detail_result)
        harvest_object.save()
        return True

    # ------------------------------------------------------------------
    # Import stage
    # ------------------------------------------------------------------
    def import_stage(self, harvest_object) -> bool:
        log.info("Importing MLIT dataset (guid=%s)", harvest_object.guid)

        if not harvest_object.content:
            message = f"No content to import for object {harvest_object.id}"
            log.error(message)
            self._save_object_error(message, harvest_object, "Import")
            return False

        try:
            dataset = json.loads(harvest_object.content)
        except ValueError as err:
            message = f"Dataset JSON could not be decoded: {err}"
            log.error(message)
            self._save_object_error(message, harvest_object, "Import")
            return False

        try:
            package_dict = self._make_package_dict(dataset, harvest_object)
        except Exception as err:  # noqa: BLE001 - surfacing mapping issues for later adjustment
            message = f"Failed to map dataset {harvest_object.guid} to CKAN package: {err}"
            log.exception(message)
            self._save_object_error(message, harvest_object, "Import")
            return False

        # Ensure we have a dataset name to satisfy CKAN validation
        package_dict.setdefault(
            "name",
            self._gen_new_name(package_dict.get("title") or harvest_object.guid),
        )
        package_dict.setdefault("id", harvest_object.guid)

        return self._create_or_update_package(package_dict, harvest_object)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _load_config(self, raw_config: Optional[str]) -> Dict[str, Any]:
        if not raw_config:
            config: Dict[str, Any] = {}
        else:
            try:
                config = json.loads(raw_config)
            except ValueError as err:
                raise ValueError(f"Invalid JSON: {err}") from err

        api_base = config.get("api_base") or DEFAULT_API_BASE
        config["api_base"] = api_base.rstrip("/")

        datasets_path = (
            config.get("datasets_path")
            or config.get("dataset_path")
            or DEFAULT_DATASET_PATH
        )
        config["datasets_path"] = str(datasets_path).strip("/")

        search_path = config.get("search_path")
        if search_path is None:
            search_path = config.get("dataset_path") or DEFAULT_SEARCH_PATH
        config["search_path"] = str(search_path).strip("/") if search_path else ""

        detail_template = (
            config.get("detail_path_template")
            or config.get("detail_template")
            or DEFAULT_DETAIL_TEMPLATE
        )
        config["detail_path_template"] = str(detail_template)

        detail_result_path = config.get("detail_result_path") or DEFAULT_DETAIL_RESULT_PATH
        config["detail_result_path"] = detail_result_path

        dataset_entries_path = config.get("dataset_entries_path")
        config["dataset_entries_path"] = dataset_entries_path

        dataset_guid_path = config.get("dataset_guid_path")
        config["dataset_guid_path"] = dataset_guid_path

        api_key_header = config.get("api_key_header") or DEFAULT_API_KEY_HEADER
        config["api_key_header"] = api_key_header

        extra_headers = config.get("extra_headers")
        config["extra_headers"] = extra_headers if isinstance(extra_headers, dict) else None

        api_key_query_param = config.get("api_key_query_param")
        config["api_key_query_param"] = (
            str(api_key_query_param) if api_key_query_param else None
        )

        http_method = str(config.get("http_method", DEFAULT_HTTP_METHOD)).upper()
        config["http_method"] = http_method

        detail_http_method = str(config.get("detail_http_method", http_method)).upper()
        config["detail_http_method"] = detail_http_method

        config["search_query"] = config.get("search_query")
        config["search_variables"] = config.get("search_variables")
        config["search_payload"] = config.get("search_payload")
        config["search_term"] = config.get("search_term", "")

        config["detail_query"] = config.get("detail_query")
        config["detail_variables"] = config.get("detail_variables")
        config["detail_payload"] = config.get("detail_payload")

        try:
            page_size = int(config.get("page_size", 100))
        except (TypeError, ValueError):
            page_size = 100
        config["page_size"] = max(page_size, 1)

        since = config.get("since")
        if since:
            config["since"] = str(since)

        api_key = config.get("api_key") or toolkit_config.get("mlit.api_key")
        if api_key:
            config["api_key"] = str(api_key)

        self.config = config
        return config

    def _get_http_session(self, config: Dict[str, Any]) -> Session:
        session = requests.Session()
        headers = {
            "Accept": "application/json",
            "User-Agent": "ckanext-mlit-harvester/0.1.0",
        }
        api_key = config.get("api_key")
        if api_key:
            header_name = config.get("api_key_header") or DEFAULT_API_KEY_HEADER
            if header_name:
                headers[str(header_name)] = api_key
        if config.get("extra_headers"):
            headers.update({str(k): v for k, v in config["extra_headers"].items()})
        session.headers.update(headers)
        return session

    def _build_endpoint(self, config: Dict[str, Any], path: Optional[str]) -> Optional[str]:
        base_url = config.get("api_base")
        if not base_url:
            return None
        normalized_path = path or ""
        return urljoin(base_url + "/", normalized_path)

    def _listing_params(self, config: Dict[str, Any], page: int) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if config.get("http_method", DEFAULT_HTTP_METHOD).upper() != "POST":
            params["page"] = page
            params["page_size"] = config["page_size"]
        if config.get("api_key_query_param") and config.get("api_key"):
            params[config["api_key_query_param"]] = config["api_key"]
        if config.get("query"):
            params["query"] = config["query"]
        if config.get("since"):
            # NOTE: Update parameter name to match the MLIT API (eg. updated_since, last_modified).
            params["updated_since"] = config["since"]
        return params

    def _detail_params(self, config: Dict[str, Any]) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if config.get("api_key_query_param") and config.get("api_key"):
            params[config["api_key_query_param"]] = config["api_key"]
        # NOTE: Add extra detail-level query parameters if required by MLIT's API.
        return params

    def _send_request(
        self,
        session: Session,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_payload: Optional[Dict[str, Any]] = None,
        method: str = DEFAULT_HTTP_METHOD,
    ) -> Any:
        method_upper = (method or DEFAULT_HTTP_METHOD).upper()
        log.debug(
            "Requesting %s method=%s params=%s payload_present=%s",
            url,
            method_upper,
            params,
            json_payload is not None,
        )
        try:
            if method_upper == "POST":
                response: Response = session.post(
                    url,
                    params=params,
                    json=json_payload if json_payload is not None else {},
                    timeout=REQUEST_TIMEOUT,
                )
            else:
                response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except RequestException as err:
            raise RuntimeError(f"HTTP request failed: {err}") from err

        try:
            return response.json()
        except ValueError as err:
            raise RuntimeError(f"Response was not valid JSON: {err}") from err

    def _extract_dataset_entries(self, data: Any, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not data:
            return []

        entries_path = config.get("dataset_entries_path")
        if entries_path:
            data = self._pluck(data, entries_path)

        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]

        if isinstance(data, dict):
            for key in ("results", "datasets", "items", "data"):
                value = data.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
            result = data.get("result")
            if isinstance(result, dict):
                results = result.get("results")
                if isinstance(results, list):
                    return [item for item in results if isinstance(item, dict)]

        return []

    def _extract_dataset_guid(self, dataset: Dict[str, Any], config: Dict[str, Any]) -> Optional[str]:
        guid_path = config.get("dataset_guid_path")
        if guid_path:
            value = self._pluck(dataset, guid_path)
            if value:
                return str(value)
        for key in ("id", "identifier", "dataset_id", "resource_id"):
            value = dataset.get(key)
            if value:
                return str(value)
        return None

    def _build_search_payload(self, config: Dict[str, Any], page: int) -> Optional[Dict[str, Any]]:
        context = {
            "page": page,
            "page_size": config["page_size"],
            "size": config["page_size"],
            "offset": (page - 1) * config["page_size"],
            "term": config.get("search_term", ""),
        }
        has_custom_payload = any(
            config.get(key) is not None for key in ("search_query", "search_payload")
        )
        if not has_custom_payload and config.get("search_variables") is None:
            return None

        payload: Dict[str, Any] = {}
        if config.get("search_query"):
            payload["query"] = self._render_template(config["search_query"], context)
        if config.get("search_variables") is not None:
            payload["variables"] = self._render_template(config["search_variables"], context)
        if config.get("search_payload"):
            extra_payload = self._render_template(config["search_payload"], context)
            if isinstance(extra_payload, dict):
                payload.update(extra_payload)
        return payload if payload else None

    def _build_detail_payload(self, config: Dict[str, Any], guid: str) -> Optional[Dict[str, Any]]:
        context = {
            "guid": guid,
            "id": guid,
        }
        has_custom_payload = any(
            config.get(key) is not None for key in ("detail_query", "detail_payload")
        )
        if not has_custom_payload and config.get("detail_variables") is None:
            return None

        payload: Dict[str, Any] = {}
        if config.get("detail_query"):
            payload["query"] = self._render_template(config["detail_query"], context)
        if config.get("detail_variables") is not None:
            payload["variables"] = self._render_template(config["detail_variables"], context)
        if config.get("detail_payload"):
            extra_payload = self._render_template(config["detail_payload"], context)
            if isinstance(extra_payload, dict):
                payload.update(extra_payload)
        return payload if payload else None

    def _render_template(self, value: Any, context: Dict[str, Any]) -> Any:
        if isinstance(value, str):
            try:
                return value.format(**context)
            except Exception:  # noqa: BLE001 - fall back to original string if formatting fails
                return value
        if isinstance(value, list):
            return [self._render_template(item, context) for item in value]
        if isinstance(value, dict):
            return {key: self._render_template(val, context) for key, val in value.items()}
        return value

    def _pluck(self, data: Any, path: Optional[str]) -> Any:
        if path in (None, ""):
            return data
        current = data
        for segment in path.split('.'):
            if isinstance(current, dict) and segment in current:
                current = current[segment]
            else:
                return None
        return current

    def _make_package_dict(
        self,
        dataset: Dict[str, Any],
        harvest_object: HarvestObject,
    ) -> Dict[str, Any]:
        # NOTE: Replace placeholder mappings with MLIT API field names.
        title = dataset.get("title") or dataset.get("name") or harvest_object.guid
        description = dataset.get("description") or dataset.get("notes") or ""

        package_dict: Dict[str, Any] = {
            "id": dataset.get("id", harvest_object.guid),
            "title": title,
            "notes": description,
            "license_id": dataset.get("license_id") or dataset.get("license"),
            "tags": self._format_tags(dataset.get("tags")),
            "extras": self._make_extras(dataset),
            "resources": self._make_resources(dataset),
        }

        remote_name = dataset.get("name")
        if remote_name:
            package_dict["name"] = remote_name
        else:
            package_dict["name"] = self._gen_new_name(title)

        owner_org = dataset.get("organization") or dataset.get("owner_org")
        if isinstance(owner_org, dict):
            package_dict["owner_org"] = owner_org.get("id") or owner_org.get("name")
        elif isinstance(owner_org, str):
            package_dict["owner_org"] = owner_org

        return package_dict

    def _format_tags(self, raw_tags: Any) -> List[Dict[str, str]]:
        tags: List[Dict[str, str]] = []
        if not raw_tags:
            return tags

        if isinstance(raw_tags, list):
            for tag in raw_tags:
                if isinstance(tag, dict):
                    value = tag.get("name") or tag.get("display_name")
                else:
                    value = str(tag)
                if value:
                    tags.append({"name": value})
        elif isinstance(raw_tags, str):
            tags.append({"name": raw_tags})

        return tags

    def _make_extras(self, dataset: Dict[str, Any]) -> List[Dict[str, Any]]:
        extras: List[Dict[str, Any]] = []

        # NOTE: Add MLIT-specific metadata fields here. Example placeholders:
        placeholder_fields = {
            # "mlit_field": "ckan_extra_key",
            # "mlit_subtitle": "subtitle",
            # "mlit_theme": "theme",
        }

        for source_key, extra_key in placeholder_fields.items():
            value = dataset.get(source_key)
            if value is not None:
                extras.append({"key": extra_key, "value": value})

        # Preserve upstream extras if already provided in CKAN format.
        if isinstance(dataset.get("extras"), list):
            for extra in dataset["extras"]:
                if isinstance(extra, dict) and {"key", "value"} <= extra.keys():
                    extras.append({"key": extra["key"], "value": extra.get("value")})

        return extras

    def _make_resources(self, dataset: Dict[str, Any]) -> List[Dict[str, Any]]:
        resources: List[Dict[str, Any]] = []
        raw_resources = dataset.get("resources") or dataset.get("files")

        if not isinstance(raw_resources, (list, tuple)):
            return resources

        for index, resource in enumerate(raw_resources, start=1):
            if not isinstance(resource, dict):
                continue

            url = resource.get("url") or resource.get("download_url")
            if not url:
                log.warning(
                    "Skipping MLIT resource without URL (dataset=%s, resource=%r)",
                    dataset.get("id"),
                    resource,
                )
                continue

            resource_dict: Dict[str, Any] = {
                "url": url,
                "name": resource.get("name") or resource.get("title") or f"resource-{index}",
                "description": resource.get("description") or resource.get("notes"),
                "format": resource.get("format") or resource.get("mimetype"),
                "mime_type": resource.get("mimetype"),
            }

            # NOTE: Extend resource mapping (eg. size, language, temporal coverage) with real MLIT fields.

            resources.append(resource_dict)

        return resources
