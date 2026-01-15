#!/usr/bin/env python3
"""
Utility to publish or update a CKAN dataset containing a 3DCityDB web map export.

The script accepts a JSON configuration with the following structure:
{
  "ckan_url": "https://ckan.example.com",
  "api_key": "TOKEN",
  "owner_org": "planning",
  "dataset": {
    "name": "city-3d",
    "title": "City 3D Model",
    "notes": "LOD2 buildings",
    "tags": ["3d", "citygml"],
    "extras": {"lod_available": "1,2"}
  },
  "resources": [
    {
      "name": "3D Viewer",
      "url": "https://ckan.example.com/3d/city/index.html",
      "format": "HTML",
      "mimetype": "text/html",
      "description": "Embedded Cesium app"
    },
    {
      "name": "Cesium Tileset",
      "url": "https://ckan.example.com/3d/city/tiles/tileset.json",
      "format": "3D Tiles",
      "mimetype": "application/json",
      "description": "3D Tileset for external use",
      "create_view": true
    }
  ],
  "thumbnail": "/path/to/thumbnail.png"
}

If a resource entry contains "create_view": true, the script will ensure a
Cesium viewer resource view exists for the resource, using the optional
"tileset_url" property if provided.
"""

import argparse
import json
import os
import pathlib
from typing import Any, Dict, Iterable, Optional

import requests


class CkanClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": api_key})

    def action(self, name: str, **payload: Any) -> Dict[str, Any]:
        url = f"{self.base_url}/api/3/action/{name}"
        response = self.session.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            raise RuntimeError(f"CKAN action {name} failed: {data}")
        return data["result"]

    def package_show(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self.action("package_show", id=dataset_id)
        except requests.HTTPError as exc:  # type: ignore[attr-defined]
            if exc.response is not None and exc.response.status_code == 404:
                return None
            raise

    def resource_search(self, package_id: str) -> Iterable[Dict[str, Any]]:
        package = self.action("package_show", id=package_id)
        return package.get("resources", [])

    def ensure_dataset(self, owner_org: Optional[str], dataset_cfg: Dict[str, Any]) -> Dict[str, Any]:
        dataset_id = dataset_cfg.get("name") or dataset_cfg.get("id")
        if not dataset_id:
            raise ValueError("dataset.name must be provided in the config")

        existing = self.package_show(dataset_id)
        payload = dataset_cfg.copy()
        if owner_org:
            payload.setdefault("owner_org", owner_org)

        if existing:
            payload["id"] = existing["id"]
            result = self.action("package_patch", **payload)
        else:
            result = self.action("package_create", **payload)
        return result

    def ensure_resource(self, package_id: str, resource_cfg: Dict[str, Any]) -> Dict[str, Any]:
        resources = list(self.resource_search(package_id))
        target = None
        for res in resources:
            if res.get("name") == resource_cfg.get("name"):
                target = res
                break

        payload = resource_cfg.copy()
        payload.setdefault("package_id", package_id)
        if target:
            payload.setdefault("id", target["id"])
            result = self.action("resource_patch", **payload)
        else:
            result = self.action("resource_create", **payload)
        return result

    def ensure_resource_view(self, resource_id: str, resource_name: str, tileset_url: Optional[str] = None, allow_fullscreen: bool = True) -> Dict[str, Any]:
        existing_views = self.action("resource_view_list", id=resource_id)
        for view in existing_views:
            if view.get("view_type") == "cesium_viewer":
                update_payload = {
                    "id": view["id"],
                    "title": view.get("title") or f"3D View - {resource_name}",
                    "resource_id": resource_id,
                    "view_type": "cesium_viewer",
                }
                if tileset_url:
                    update_payload["tileset_url"] = tileset_url
                update_payload["allow_fullscreen"] = allow_fullscreen
                return self.action("resource_view_update", **update_payload)

        create_payload = {
            "resource_id": resource_id,
            "title": f"3D View - {resource_name}",
            "view_type": "cesium_viewer",
            "allow_fullscreen": allow_fullscreen,
        }
        if tileset_url:
            create_payload["tileset_url"] = tileset_url
        return self.action("resource_view_create", **create_payload)

    def update_thumbnail(self, dataset_id: str, thumbnail_path: str) -> None:
        with open(thumbnail_path, "rb") as fh:
            files = {"image_upload": fh}
            payload = {"id": dataset_id}
            url = f"{self.base_url}/api/3/action/package_patch"
            response = self.session.post(url, data=payload, files=files, timeout=60)
            response.raise_for_status()
            data = response.json()
            if not data.get("success"):
                raise RuntimeError(f"Thumbnail upload failed: {data}")


def load_config(path: pathlib.Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish 3D web map artifacts to CKAN")
    parser.add_argument("config", type=pathlib.Path, help="Path to JSON config file")
    args = parser.parse_args()

    cfg = load_config(args.config)

    ckan_url = cfg.get("ckan_url") or os.environ.get("CKAN_URL")
    api_key = cfg.get("api_key") or os.environ.get("CKAN_API_KEY")
    owner_org = cfg.get("owner_org")

    if not ckan_url:
        raise SystemExit("ckan_url must be provided via config or CKAN_URL env var")
    if not api_key:
        raise SystemExit("api_key must be provided via config or CKAN_API_KEY env var")

    client = CkanClient(ckan_url, api_key)

    dataset_cfg = cfg.get("dataset") or {}
    dataset = client.ensure_dataset(owner_org, dataset_cfg)

    created_resources = []
    for resource_cfg in cfg.get("resources", []):
        resource = client.ensure_resource(dataset["id"], resource_cfg)
        created_resources.append((resource, resource_cfg))

    for resource, resource_cfg in created_resources:
        if resource_cfg.get("create_view"):
            tileset_url = resource_cfg.get("tileset_url")
            allow_fullscreen = resource_cfg.get("allow_fullscreen", True)
            client.ensure_resource_view(resource["id"], resource["name"], tileset_url=tileset_url, allow_fullscreen=allow_fullscreen)

    thumbnail_path = cfg.get("thumbnail")
    if thumbnail_path:
        path = pathlib.Path(thumbnail_path)
        if not path.is_file():
            raise SystemExit(f"Thumbnail {thumbnail_path} not found")
        client.update_thumbnail(dataset["id"], thumbnail_path)

    print(f"Published dataset '{dataset['name']}' with {len(created_resources)} resources")


if __name__ == "__main__":
    main()
