# -*- coding: utf-8 -*-

"""Simple harvester that ingests a single CSV file into CKAN."""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from requests import RequestException

import ckan.plugins.toolkit as tk

from ckanext.harvest.harvesters.base import HarvesterBase
from ckanext.harvest.model import HarvestObject

log = logging.getLogger(__name__)


class CSVFileHarvester(HarvesterBase):
    """Harvest a single CSV file and expose it as a CKAN dataset."""

    def info(self) -> Dict[str, str]:
        return {
            "name": "csv_file",
            "title": "CSV File Harvester",
            "description": "Fetch a CSV (or any text file) and publish/update a CKAN dataset with one resource.",
        }

    # ------------------------------------------------------------------
    # Gather
    # ------------------------------------------------------------------
    def gather_stage(self, harvest_job) -> List[str]:
        try:
            config = self._load_config(harvest_job.source.config)
        except ValueError as err:
            message = f"Invalid harvest source configuration: {err}"
            log.error(message)
            self._save_gather_error(message, harvest_job)
            return []

        guid = config["dataset_guid"]
        harvest_object = HarvestObject(guid=guid, job=harvest_job)
        harvest_object.save()
        return [harvest_object.id]

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------
    def fetch_stage(self, harvest_object) -> bool:
        try:
            config = self._load_config(harvest_object.source.config)
        except ValueError as err:
            message = f"Invalid stored configuration: {err}"
            log.error(message)
            self._save_object_error(message, harvest_object, "Fetch")
            return False

        try:
            response = requests.get(
                config["source_url"],
                timeout=config["timeout"],
                headers=config["request_headers"],
            )
            response.raise_for_status()
        except RequestException as err:  # pragma: no cover - network call
            message = f"Failed to download CSV from {config['source_url']}: {err}"
            log.error(message)
            self._save_object_error(message, harvest_object, "Fetch")
            return False

        harvest_object.content = response.text
        harvest_object.save()
        return True

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------
    def import_stage(self, harvest_object) -> bool:
        try:
            config = self._load_config(harvest_object.source.config)
        except ValueError as err:
            message = f"Failed to load configuration during import: {err}"
            log.error(message)
            self._save_object_error(message, harvest_object, "Import")
            return False

        if not harvest_object.content:
            message = "CSV download produced no content"
            log.error(message)
            self._save_object_error(message, harvest_object, "Import")
            return False

        package_dict: Dict[str, Any] = {
            "name": config["dataset_name"],
            "title": config["dataset_title"],
            "notes": config.get("dataset_notes", ""),
        }

        package_dict["id"] = config["dataset_guid"]

        owner_org = config.get("owner_org")
        if owner_org:
            package_dict["owner_org"] = owner_org

        extras = config.get("extras", {})
        if extras:
            package_dict["extras"] = [
                {"key": key, "value": value}
                for key, value in extras.items()
            ]

        resource_dict: Dict[str, Any] = {
            "name": config.get("resource_name") or config["dataset_title"],
            "description": config.get("resource_description", ""),
            "format": config.get("resource_format", "CSV"),
        }

        existing_resource_id = self._find_existing_resource_id(
            config["dataset_guid"],
            resource_dict["name"],
            resource_dict["format"],
        )
        if existing_resource_id:
            resource_dict["id"] = existing_resource_id

        temp_upload: Optional[Path] = None
        upload_handle = None
        if config.get("mirror_locally"):
            with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
                tmp.write(harvest_object.content)
                temp_upload = Path(tmp.name)

            upload_handle = temp_upload.open("rb")
            resource_dict["upload"] = upload_handle
            resource_dict["url"] = "upload"
        else:
            resource_dict["url"] = config["source_url"]

        package_dict["resources"] = [resource_dict]

        result = self._create_or_update_package(
            package_dict,
            harvest_object,
            package_dict_form="package_show",
        )

        if upload_handle:
            try:
                upload_handle.close()
            except Exception:  # pragma: no cover - best effort cleanup
                pass
        if temp_upload is not None:
            try:
                temp_upload.unlink(missing_ok=True)
            except Exception as err:  # pragma: no cover - cleanup best effort
                log.warning("Failed to remove temp file %s: %s", temp_upload, err)

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _load_config(self, raw: Optional[str]) -> Dict[str, Any]:
        if not raw:
            raise ValueError("Configuration is empty")

        if isinstance(raw, dict):
            config = raw
        else:
            try:
                config = json.loads(raw)
            except json.JSONDecodeError:
                config = json.loads(bytes(raw, "utf-8").decode("unicode_escape"))

        if not config.get("source_url"):
            raise ValueError("'source_url' is required")

        if not config.get("dataset_name"):
            raise ValueError("'dataset_name' is required")

        config.setdefault("dataset_title", config["dataset_name"].replace("-", " ").title())
        config.setdefault("dataset_guid", config["dataset_name"])

        # Runtime defaults
        config.setdefault("timeout", 60)
        config.setdefault("request_headers", {})
        config.setdefault("resource_format", "CSV")
        config.setdefault("mirror_locally", False)

        if config.get("extra_headers") and not config.get("request_headers"):
            config["request_headers"] = config["extra_headers"]

        headers = {}
        for header_dict in (
            config.get("request_headers"),
            config.get("extra_headers"),
        ):
            if isinstance(header_dict, dict):
                headers.update({str(k): str(v) for k, v in header_dict.items()})

        config["request_headers"] = headers
        config["mirror_locally"] = bool(config.get("mirror_locally"))

        return config

    def _find_existing_resource_id(
        self,
        dataset_id: str,
        resource_name: str,
        resource_format: str,
    ) -> Optional[str]:
        """Try to reuse an existing resource so its UUID (and views) stay stable."""
        if not dataset_id:
            return None

        context: Dict[str, Any] = {"ignore_auth": True}
        try:
            existing_package = tk.get_action("package_show")(
                context, {"id": dataset_id}
            )
        except tk.ObjectNotFound:
            return None
        except Exception as err:  # noqa: BLE001 - defensive logging
            log.warning(
                "CSV harvester: failed to inspect package %s: %s",
                dataset_id,
                err,
            )
            return None

        resources = existing_package.get("resources") or []
        if not resources:
            return None

        def _normalized(value: Optional[str]) -> str:
            return (value or "").strip().lower()

        name_lower = _normalized(resource_name)
        format_lower = _normalized(resource_format)

        for res in resources:
            if _normalized(res.get("name")) == name_lower:
                return res.get("id")

        for res in resources:
            if _normalized(res.get("format")) == format_lower:
                return res.get("id")

        first_id = resources[0].get("id")
        return first_id if isinstance(first_id, str) else None
