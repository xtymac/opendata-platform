import os
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple
import json
from urllib.parse import urlparse

import requests
from ckan.plugins import implements, toolkit
from ckan.plugins import SingletonPlugin
from ckan import model as ckan_model
from ckan.plugins.interfaces import (
    IActions,
    IBlueprint,
    IConfigurer,
    IResourceController,
    ITemplateHelpers,
    ITranslation,
)
from ckan.lib.plugins import DefaultTranslation
from flask import Blueprint, Response, jsonify, request

from . import model as assistant_model
from ckan.lib import uploader


@toolkit.chained_action
def _config_option_update_with_cover(
    action, context: Dict[str, Any], data_dict: Dict[str, Any]
) -> Dict[str, Any]:
    cover_upload = uploader.get_uploader("admin")
    cover_upload.update_data_dict(
        data_dict,
        "ckanext.assistant.cover_image",
        "cover_image_upload",
        "clear_cover_image_upload",
    )

    result = action(context, data_dict)

    cover_upload.upload(uploader.get_max_image_size())

    return result

ASSISTANT_BLUEPRINT = Blueprint("assistant", __name__)


def assistant_cover_image_url() -> str:
    """Return the resolved homepage cover image URL with sensible fallbacks."""
    placeholder = "/base/images/placeholder-420x220.png"

    value = toolkit.config.get("ckanext.assistant.cover_image")
    if not value:
        return placeholder

    trimmed = value.strip()
    if not trimmed:
        return placeholder

    if trimmed.startswith(("http://", "https://")):
        return trimmed

    if trimmed.startswith("/"):
        return trimmed

    return f"/uploads/admin/{trimmed}"


def _assistant_service_url() -> str:
    config = toolkit.config
    return config.get(
        "ckanext.assistant.service_url",
        os.getenv("CKAN_ASSISTANT_SERVICE_URL", "http://assistant:8000"),
    ).rstrip("/")


def _get_current_user_id() -> Optional[str]:
    """Get current logged-in user ID."""
    try:
        user_obj = toolkit.g.userobj
        return user_obj.id if user_obj else None
    except Exception:
        return None


@ASSISTANT_BLUEPRINT.route("/assistant/chat", methods=["POST"])
def proxy_chat() -> Response:
    payload: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
    service_url = _assistant_service_url() + "/chat"

    user_id = _get_current_user_id()
    conversation_id = payload.get("conversation_id")

    # Create new conversation if needed
    if user_id and not conversation_id:
        message = payload.get("message", "")
        title = message[:50] + "..." if len(message) > 50 else message
        conv = assistant_model.Conversation.create(user_id, title)
        conversation_id = conv.id

    try:
        upstream = requests.post(service_url, json=payload, timeout=30)
        upstream.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        toolkit.error("Assistant upstream request failed: %s", exc)
        return jsonify({"error": "assistant_unavailable"}), 502

    data = upstream.json()

    # Save messages to database if user is logged in
    if user_id and conversation_id:
        try:
            # Save user message
            assistant_model.Message.create(
                conversation_id=conversation_id,
                role="user",
                content=payload.get("message", "")
            )

            # Save assistant response
            assistant_model.Message.create(
                conversation_id=conversation_id,
                role="assistant",
                content=data.get("reply", ""),
                sources=data.get("sources", [])
            )

            # Update conversation timestamp
            conv = assistant_model.Conversation.get(conversation_id)
            if conv:
                import datetime
                conv.updated_at = datetime.datetime.utcnow()
                conv.save()

        except Exception as exc:  # noqa: BLE001
            toolkit.error("Failed to save conversation: %s", exc)

    # Include conversation_id in response
    data["conversation_id"] = conversation_id

    return jsonify(data)


@ASSISTANT_BLUEPRINT.route("/assistant/conversations", methods=["GET"])
def list_conversations() -> Response:
    """List all conversations for current user."""
    user_id = _get_current_user_id()
    if not user_id:
        return jsonify({"error": "not_authenticated"}), 401

    try:
        conversations = assistant_model.Conversation.get_for_user(user_id)
        return jsonify({
            "conversations": [conv.to_dict() for conv in conversations]
        })
    except Exception as exc:  # noqa: BLE001
        toolkit.error("Failed to list conversations: %s", exc)
        return jsonify({"error": "database_error"}), 500


@ASSISTANT_BLUEPRINT.route("/assistant/conversation/<conversation_id>", methods=["GET"])
def get_conversation(conversation_id: str) -> Response:
    """Get conversation with all messages."""
    user_id = _get_current_user_id()
    if not user_id:
        return jsonify({"error": "not_authenticated"}), 401

    try:
        conv = assistant_model.Conversation.get(conversation_id)
        if not conv or conv.user_id != user_id:
            return jsonify({"error": "not_found"}), 404

        messages = assistant_model.Message.get_for_conversation(conversation_id)

        return jsonify({
            "conversation": conv.to_dict(),
            "messages": [msg.to_dict() for msg in messages]
        })
    except Exception as exc:  # noqa: BLE001
        toolkit.error("Failed to get conversation: %s", exc)
        return jsonify({"error": "database_error"}), 500


@ASSISTANT_BLUEPRINT.route("/assistant/conversation/<conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id: str) -> Response:
    """Delete a conversation."""
    user_id = _get_current_user_id()
    if not user_id:
        return jsonify({"error": "not_authenticated"}), 401

    try:
        conv = assistant_model.Conversation.get(conversation_id)
        if not conv or conv.user_id != user_id:
            return jsonify({"error": "not_found"}), 404

        conv.delete()
        conv.commit()

        return jsonify({"success": True})
    except Exception as exc:  # noqa: BLE001
        toolkit.error("Failed to delete conversation: %s", exc)
        return jsonify({"error": "database_error"}), 500


@ASSISTANT_BLUEPRINT.route("/assistant/healthz", methods=["GET"])
def proxy_health() -> Response:
    service_url = _assistant_service_url() + "/healthz"

    try:
        upstream = requests.get(service_url, timeout=5)
        upstream.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        toolkit.error("Assistant health check failed: %s", exc)
        return jsonify({"status": "down"}), 502

    return jsonify({"status": "ok"})


@ASSISTANT_BLUEPRINT.route("/assistant/sync", methods=["POST"])
def proxy_sync() -> Response:
    """Proxy sync request to cms-sync-web service."""
    sync_url = os.getenv("CMS_SYNC_URL", "http://cms-sync-web:8080") + "/api/sync"
    sync_user = os.getenv("CMS_SYNC_USER", "admin")
    sync_pass = os.getenv("CMS_SYNC_PASS", "Yamaguchi2025!")

    payload: Dict[str, Any] = request.get_json(force=True, silent=True) or {}

    try:
        upstream = requests.post(
            sync_url,
            json=payload,
            auth=(sync_user, sync_pass),
            timeout=60
        )
        return jsonify(upstream.json()), upstream.status_code
    except Exception as exc:  # noqa: BLE001
        toolkit.error("CMS sync request failed: %s", exc)
        return jsonify({"error": str(exc)}), 502


DEFAULT_AUTO_VIEW_MAP: Dict[str, Tuple[str, ...]] = {
    "csv": ("recline_view",),
    "tsv": ("recline_view",),
    "json": ("text_view",),
    "geojson": ("geo_view",),
    "kml": ("geo_view",),
    "kmz": ("geo_view",),
    "png": ("image_view",),
    "jpg": ("image_view",),
    "jpeg": ("image_view",),
    "gif": ("image_view",),
    "txt": ("text_view",),
}

VIEW_TITLE_SUFFIXES: Dict[str, str] = {
    "datatables_view": "Table",
    "recline_view": "Explorer",
    "recline_graph_view": "Chart",
    "geo_view": "Map",
    "simple_map": "Map",
    "image_view": "Image",
    "text_view": "Preview",
    "cesium_viewer": "3D",
}


class AssistantPlugin(SingletonPlugin, DefaultTranslation):
    implements(IConfigurer)
    implements(ITemplateHelpers)
    implements(IActions)
    implements(IBlueprint)
    implements(IResourceController, inherit=True)
    implements(ITranslation, inherit=True)

    def i18n_directory(self) -> str:
        """Return the directory containing compiled translation files."""
        return os.path.join(os.path.dirname(__file__), "i18n")

    def update_config(self, config: Dict[str, Any]) -> None:
        toolkit.add_template_directory(config, "templates")
        toolkit.add_public_directory(config, "public")

        footer_key = "ckan.template_footer_end"
        snippet = "ckanext_assistant/footer.html"
        current = config.get(footer_key, "").strip()
        if snippet not in current.split():
            config[footer_key] = (current + " " + snippet).strip()

        config.setdefault("ckanext.assistant.service_url", _assistant_service_url())

        # Initialize database tables
        try:
            assistant_model.init_tables()
        except Exception as exc:  # noqa: BLE001
            import logging
            log = logging.getLogger(__name__)
            log.error("Failed to initialize assistant tables: %s", exc)

    def update_config_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        ignore_missing = toolkit.get_validator("ignore_missing")
        unicode_safe = toolkit.get_validator("unicode_safe")

        schema["ckanext.assistant.cover_image"] = [ignore_missing, unicode_safe]
        schema["cover_image_upload"] = [ignore_missing, unicode_safe]
        schema["clear_cover_image_upload"] = [ignore_missing, unicode_safe]

        return schema

    def get_blueprint(self) -> Blueprint:
        return ASSISTANT_BLUEPRINT

    # ITemplateHelpers

    def get_helpers(self) -> Dict[str, Any]:
        return {"assistant_cover_image_url": assistant_cover_image_url}

    # IActions

    def get_actions(self) -> Dict[str, Any]:
        return {"config_option_update": _config_option_update_with_cover}

    # IResourceController

    def after_create(self, context: Dict[str, Any], resource: Dict[str, Any]) -> None:
        self._ensure_auto_views(context, resource)

    def after_update(self, context: Dict[str, Any], resource: Dict[str, Any]) -> None:
        self._ensure_auto_views(context, resource)

    # Internal helpers

    @staticmethod
    @lru_cache(maxsize=1)
    def _auto_view_map() -> Dict[str, Tuple[str, ...]]:
        """Load mapping of resource formats to view types."""
        mapping: Dict[str, Tuple[str, ...]] = dict(DEFAULT_AUTO_VIEW_MAP)

        prefix = "ckanext.assistant.auto_view_map."
        config = toolkit.config

        for key in list(config):
            if not key.startswith(prefix):
                continue
            format_key = key[len(prefix) :].strip().lower()
            if not format_key:
                continue
            raw_value = config.get(key)
            if not raw_value:
                mapping.pop(format_key, None)
                continue
            view_types = AssistantPlugin._normalize_view_list(raw_value)
            if view_types:
                mapping[format_key] = tuple(view_types)

        return mapping

    @staticmethod
    def _normalize_view_list(value: Any) -> List[str]:
        """Turn config strings/iterables into a normalized list of view types."""
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",")]
        elif isinstance(value, Iterable):
            items = [str(item).strip() for item in value]
        else:
            return []
        return [item for item in items if item]

    @staticmethod
    def _collect_format_keys(resource: Dict[str, Any]) -> List[str]:
        """Collect possible format identifiers for a resource."""
        candidates: List[str] = []
        seen: set[str] = set()

        def _add(value: Optional[str]) -> None:
            if not value:
                return
            lowered = value.strip().lower()
            if not lowered or lowered in seen:
                return
            seen.add(lowered)
            candidates.append(lowered)

        for key in ("format", "mimetype", "mimetype_inner"):
            raw = resource.get(key)
            if isinstance(raw, str):
                _add(raw)

        url = resource.get("url")
        if isinstance(url, str):
            path = urlparse(url).path
            if path:
                _, ext = os.path.splitext(path)
                if ext:
                    _add(ext.lstrip("."))

        return candidates

    @staticmethod
    def _default_title(resource: Dict[str, Any], view_type: str) -> str:
        base = (
            resource.get("name")
            or resource.get("title")
            or resource.get("id")
            or "Resource"
        )
        suffix = VIEW_TITLE_SUFFIXES.get(
            view_type, view_type.replace("_", " ").title()
        )
        return f"{base} - {suffix}"

    def _ensure_auto_views(
        self, context: Dict[str, Any], resource: Dict[str, Any]
    ) -> None:
        if not resource or not resource.get("id"):
            return

        format_keys = self._collect_format_keys(resource)
        if not format_keys:
            return

        mapping = self._auto_view_map()
        desired_views: List[str] = []
        for key in format_keys:
            desired_views.extend(mapping.get(key, ()))

        if not desired_views:
            return

        unique_view_types: List[str] = []
        seen_view_types: set[str] = set()
        for view_type in desired_views:
            if view_type not in seen_view_types:
                seen_view_types.add(view_type)
                unique_view_types.append(view_type)

        if not unique_view_types:
            return

        auth_user_obj = context.get("auth_user_obj")
        user_name = (
            context.get("user")
            or toolkit.config.get("ckanext.assistant.auto_view_user")
            or (getattr(auth_user_obj, "name", None) if auth_user_obj else None)
            or getattr(toolkit.g, "user", None)
            or "harvest"
        )

        action_context: Dict[str, Any] = {
            "model": context.get("model", ckan_model),
            "session": context.get("session", ckan_model.Session),
            "user": user_name,
            "ignore_auth": True,
        }

        try:
            existing = toolkit.get_action("resource_view_list")(
                action_context, {"id": resource["id"]}
            )
        except Exception as exc:  # noqa: BLE001
            toolkit.error(
                "Auto view: failed to list views for resource %s: %s",
                resource.get("id"),
                exc,
            )
            return

        existing_types = {view.get("view_type") for view in existing or []}

        for view_type in unique_view_types:
            if not view_type or view_type in existing_types:
                continue

            payload: Dict[str, Any] = {
                "resource_id": resource["id"],
                "view_type": view_type,
                "title": self._default_title(resource, view_type),
            }

            try:
                toolkit.get_action("resource_view_create")(
                    action_context, payload
                )
            except toolkit.ValidationError as exc:  # type: ignore[attr-defined]
                toolkit.error(
                    "Auto view: validation error creating %s for %s: %s",
                    view_type,
                    resource.get("id"),
                    exc.error_dict if hasattr(exc, "error_dict") else exc,
                )
            except Exception as exc:  # noqa: BLE001
                toolkit.error(
                    "Auto view: failed to create %s for %s: %s",
                    view_type,
                    resource.get("id"),
                    exc,
                )
