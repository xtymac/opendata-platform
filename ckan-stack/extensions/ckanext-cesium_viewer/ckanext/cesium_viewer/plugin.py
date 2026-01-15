import json
import logging
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

import ckan.plugins as plugins
from ckan.plugins import toolkit


log = logging.getLogger(__name__)


class CesiumViewerPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer, inherit=True)
    plugins.implements(plugins.IResourceView, inherit=True)
    plugins.implements(plugins.ITemplateHelpers, inherit=True)

    def update_config(self, config):
        toolkit.add_template_directory(config, "templates")

        default_web_root = config.get("cesium_viewer.web_root") or "/srv/app/webmaps"
        config["cesium_viewer.web_root"] = default_web_root
        Path(default_web_root).mkdir(parents=True, exist_ok=True)

        public_base = config.get("cesium_viewer.public_base_url")
        if not public_base:
            site_url = (config.get("ckan.site_url") or "").rstrip("/")
            public_base = f"{site_url}/3d" if site_url else "/3d"
            config["cesium_viewer.public_base_url"] = public_base

    def info(self):
        return {
            "name": "cesium_viewer",
            "title": "3D Cesium Viewer",
            "icon": "globe",
            "iframed": False,
            "always_available": True,
            "schema": {
                "tileset_url": [toolkit.get_validator("ignore_missing")],
                "allow_fullscreen": [toolkit.get_validator("ignore_missing")],
                "tileset_path": [toolkit.get_validator("ignore_missing")],
            },
            "default_title": "3D Viewer",
        }

    def can_view(self, data_dict):
        resource = data_dict.get("resource", {})
        fmt = (resource.get("format") or "").lower()
        mimetype = (resource.get("mimetype") or "").lower()

        viewable_formats = {"html", "htm", "3d tiles", "3d-tiles", "json"}
        if fmt in viewable_formats:
            return True
        if mimetype in {"text/html", "application/json", "application/octet-stream"}:
            return True
        url = resource.get("url") or ""
        return url.endswith(".json") or url.endswith(".html") or url.endswith(".zip")

    def view_template(self, context, data_dict):
        return "view/cesium_viewer/iframe.html"

    def form_template(self, context, data_dict):
        return "view/cesium_viewer/form.html"

    def setup_template_variables(self, context, data_dict):
        resource = data_dict.get("resource", {})
        resource_view = data_dict.get("resource_view", {})

        allow_fullscreen = self._as_bool(resource_view.get("allow_fullscreen"))

        tileset_url_cfg = self._as_single(resource_view.get("tileset_url"))
        tileset_path_cfg = self._as_single(resource_view.get("tileset_path"))

        viewer_data = {
            "resource_url": resource.get("url"),
            "tileset_url": tileset_url_cfg or resource.get("url"),
            "tileset_path": tileset_path_cfg,
            "format": (resource.get("format") or "").lower(),
            "mimetype": (resource.get("mimetype") or "").lower(),
            "allow_fullscreen": allow_fullscreen,
            "error": None,
        }

        try:
            prepared = self._prepare_resource_view(resource, resource_view)
            viewer_data.update({k: v for k, v in prepared.items() if v is not None})
        except Exception as exc:  # pylint: disable=broad-except
            log.exception("Failed preparing resource view for %s", resource.get("id"))
            viewer_data["error"] = str(exc)

        data_dict["cesium_viewer"] = viewer_data
        return data_dict

    def get_helpers(self):
        return {
            "cesium_asset_is_html": self._is_html_resource,
        }

    @staticmethod
    def _is_html_resource(resource_dict):
        fmt = (resource_dict.get("format") or "").lower()
        mimetype = (resource_dict.get("mimetype") or "").lower()
        url = resource_dict.get("url") or ""
        if fmt in {"html", "htm"}:
            return True
        if mimetype == "text/html":
            return True
        return url.endswith(".html")

    @staticmethod
    def _as_single(value):
        if isinstance(value, (list, tuple)):
            return value[-1] if value else None
        return value

    def _as_bool(self, value):
        single = self._as_single(value)
        if single is None or single == "":
            return True
        return toolkit.asbool(single)

    # Internal helpers -------------------------------------------------

    def _prepare_resource_view(self, resource, resource_view):
        if not resource:
            return {}

        result = {
            "resource_url": resource.get("url"),
            "tileset_url": self._as_single(resource_view.get("tileset_url")) or resource.get("url"),
            "tileset_path": self._as_single(resource_view.get("tileset_path")),
        }

        if self._resource_looks_like_zip(resource):
            extraction = self._ensure_zip_extracted(resource, resource_view)
            if extraction:
                result.update(extraction)
                return result
            result["error"] = toolkit._("Failed to prepare tileset from zip resource")
        return result

    def _resource_looks_like_zip(self, resource):
        url = (resource.get("url") or "").lower()
        mimetype = (resource.get("mimetype") or "").lower()
        fmt = (resource.get("format") or "").lower()
        return url.endswith(".zip") or mimetype == "application/zip" or fmt == "zip"

    def _ensure_zip_extracted(self, resource, resource_view):
        storage_root = self._web_root()
        target_dir = storage_root / "auto" / resource["id"]
        marker_path = target_dir / ".source.json"

        needs_refresh = True
        last_modified = resource.get("last_modified") or resource.get("revision_timestamp")
        source_url = resource.get("url")

        if marker_path.exists():
            try:
                marker = json.loads(marker_path.read_text(encoding="utf-8"))
                if marker.get("source_url") == source_url and marker.get("last_modified") == last_modified:
                    needs_refresh = False
            except Exception:  # pylint: disable=broad-except
                needs_refresh = True

        if needs_refresh:
            self._download_and_extract_zip(resource, target_dir)
            metadata = {"source_url": source_url, "last_modified": last_modified}
            marker_path.parent.mkdir(parents=True, exist_ok=True)
            marker_path.write_text(json.dumps(metadata), encoding="utf-8")

        tileset_info = self._locate_tileset(target_dir, resource_view)
        if not tileset_info:
            return {"error": toolkit._("tileset.json not found in extracted archive")}

        public_tileset = self._public_url_for_path(tileset_info.get("tileset")) if tileset_info.get("tileset") else None
        public_index = self._public_url_for_path(tileset_info.get("index")) if tileset_info.get("index") else None

        tileset_path_cfg = self._as_single(resource_view.get("tileset_path"))

        payload = {
            "tileset_url": public_tileset,
            "resource_url": public_index or public_tileset or resource.get("url"),
            "tileset_path": tileset_path_cfg,
        }

        tileset_path_obj = tileset_info.get("tileset")
        if (not payload.get("tileset_path")) and tileset_path_obj and tileset_path_obj.exists():
            try:
                relative_path = tileset_path_obj.resolve().relative_to(target_dir.resolve())
                payload["tileset_path"] = relative_path.as_posix()
            except ValueError:
                pass

        return payload

    def _download_and_extract_zip(self, resource, target_dir):
        url = resource.get("url")
        if not url:
            raise ValueError("Resource has no URL; cannot extract")

        resolved_url = self._resolve_absolute_url(url)
        log.info("Downloading zip resource %s to extract into %s", resolved_url, target_dir)

        temp_root = self._web_root() / "__tmp__"
        temp_root.mkdir(parents=True, exist_ok=True)
        temp_zip_path = None
        response = requests.get(resolved_url, stream=True, timeout=120)
        response.raise_for_status()
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip", dir=temp_root) as temp_fp:
                for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
                    if chunk:
                        temp_fp.write(chunk)
                temp_zip_path = Path(temp_fp.name)
        finally:
            response.close()

        tmp_extract_path = Path(tempfile.mkdtemp(dir=temp_root))
        try:
            with zipfile.ZipFile(temp_zip_path, "r") as archive:
                archive.extractall(tmp_extract_path)

            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(tmp_extract_path), str(target_dir))
        finally:
            try:
                shutil.rmtree(tmp_extract_path, ignore_errors=True)
            except OSError:
                pass
            if temp_zip_path is not None:
                try:
                    temp_zip_path.unlink()
                except OSError:
                    pass

    def _locate_tileset(self, target_dir, resource_view):
        dest = Path(target_dir)
        if not dest.exists():
            return None

        preferred = self._as_single(resource_view.get("tileset_path"))
        tileset = None
        index_html = None

        if preferred:
            candidate = dest / preferred
            if candidate.exists():
                tileset = candidate

        if not tileset:
            for path in dest.rglob("tileset.json"):
                tileset = path
                break

        for path in dest.rglob("index.html"):
            index_html = path
            break

        return {"tileset": tileset, "index": index_html}

    def _public_url_for_path(self, path_obj):
        if not path_obj:
            return None
        root = self._web_root()
        try:
            relative = Path(path_obj).resolve().relative_to(root.resolve())
        except ValueError:
            return None

        base = toolkit.config.get("cesium_viewer.public_base_url", "/3d").rstrip("/")
        return f"{base}/{relative.as_posix()}"

    def _resolve_absolute_url(self, url):
        parsed = urlparse(url)
        if parsed.scheme:
            return url
        site_url = toolkit.config.get("ckan.site_url", "").rstrip("/")
        return f"{site_url}{url}" if site_url else url

    def _web_root(self):
        root = toolkit.config.get("cesium_viewer.web_root") or "/srv/app/webmaps"
        return Path(root)
