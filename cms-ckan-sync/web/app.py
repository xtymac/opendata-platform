"""FastAPI Web UI for CMS-CKAN Sync Service"""

import hashlib
import hmac
import json
import os
import secrets
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Literal, Tuple

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Depends, HTTPException, Request, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sync_service.config import load_config, validate_config, save_runtime_config, load_runtime_config
from sync_service.core import SyncService
from sync_service.models import SyncStatusEnum
from sync_service.cms_client import CMSClient
from sync_service.ckan_client import CKANClient
from sync_service.logger import setup_logger, get_logger
from web.ckan_auth import verify_ckan_cookie

log = get_logger("cms_ckan_sync.web")

# Initialize FastAPI app
app = FastAPI(
    title="CMS-CKAN Sync Dashboard",
    description="Web interface for managing CMS to CKAN data synchronization",
    version="1.0.0"
)

# Setup security
security = HTTPBasic()
security_optional = HTTPBasic(auto_error=False)  # For optional Basic Auth fallback

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Setup static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Global service instance (will be initialized on startup)
_service: Optional[SyncService] = None
_config = None

# Thread lock for sync operations (shared by webhook and scheduler)
_sync_lock = threading.Lock()

# Global scheduler instance (only one per process)
_scheduler: Optional[BackgroundScheduler] = None


# Pydantic models for API
class SyncRequest(BaseModel):
    """Request body for sync API"""
    models: Optional[List[str]] = None
    dry_run: bool = False
    force: bool = False
    sync_mode: Literal["create", "update"] = "create"
    resource_id: Optional[str] = None  # Required when sync_mode is "update"


class SyncResponse(BaseModel):
    """Response from sync API"""
    success: bool
    message: str
    results: List[dict]


class ConfigUpdateRequest(BaseModel):
    """Request to update configuration"""
    cms_url: Optional[str] = None
    cms_token: Optional[str] = None
    ckan_url: Optional[str] = None
    ckan_token: Optional[str] = None
    ckan_organization: Optional[str] = None


class ConnectionTestRequest(BaseModel):
    """Request to test connection"""
    url: str
    token: Optional[str] = None
    organization: Optional[str] = None


class FieldMapping(BaseModel):
    """Single field mapping"""
    cms_field: str
    ckan_field: Optional[str] = None  # None means ignore


class FlexSyncRequest(BaseModel):
    """Flexible sync request"""
    cms_model_id: str
    field_mappings: List[FieldMapping] = []
    geometry_field: Optional[str] = None
    target_mode: Literal["new_dataset", "existing_dataset"]
    new_dataset_name: Optional[str] = None
    new_dataset_title: Optional[str] = None
    existing_dataset_id: Optional[str] = None
    resource_mode: Literal["new", "update"] = "new"
    existing_resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    dry_run: bool = False
    include_geojson: bool = True


class SavedJob(BaseModel):
    """Saved sync job configuration"""
    job_id: Optional[str] = None
    name: str
    config: FlexSyncRequest
    created_at: Optional[datetime] = None
    last_run: Optional[datetime] = None


def get_config():
    """Get or load configuration"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_service() -> SyncService:
    """Get or create sync service instance"""
    global _service
    if _service is None:
        config = get_config()
        setup_logger(level=config.log_level, log_dir=config.data_dir)
        _service = SyncService(config)
    return _service


async def verify_auth(
    request: Request,
    credentials: Optional[HTTPBasicCredentials] = Depends(security_optional)
) -> str:
    """
    Verify user authentication. Priority:
    1. CKAN cookie (requires sysadmin if configured)
    2. Basic Auth (fallback)

    Returns:
        Username if authenticated

    Raises:
        HTTPException: If authentication fails
    """
    config = get_config()

    # 1. Try CKAN cookie authentication
    if config.ckan_auth_enabled:
        is_valid, user_info = await verify_ckan_cookie(request, config.ckan_url)
        if is_valid and user_info:
            # Check if sysadmin is required
            if config.ckan_auth_require_sysadmin:
                if user_info.get("sysadmin"):
                    log.info(f"CKAN sysadmin auth: {user_info.get('name')}")
                    return user_info.get("name", "ckan_user")
                # Not sysadmin, continue to try Basic Auth
                log.debug(f"User {user_info.get('name')} is not sysadmin, trying Basic Auth")
            else:
                log.info(f"CKAN cookie auth: {user_info.get('name')}")
                return user_info.get("name", "ckan_user")

    # 2. Fallback to Basic Auth
    if credentials:
        expected_username = config.web_auth_username
        expected_password = config.web_auth_password

        # Use constant-time comparison to prevent timing attacks
        is_username_correct = secrets.compare_digest(
            credentials.username.encode("utf8"),
            expected_username.encode("utf8")
        )
        is_password_correct = secrets.compare_digest(
            credentials.password.encode("utf8"),
            expected_password.encode("utf8")
        )

        if is_username_correct and is_password_correct:
            log.info(f"Basic Auth successful: {credentials.username}")
            return credentials.username

    # Authentication failed
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Please login to CKAN as sysadmin or use Basic Auth.",
        headers={"WWW-Authenticate": "Basic"},
    )


# ============== Webhook & Scheduler Functions ==============

def verify_webhook_signature(request: Request, body: bytes) -> Tuple[bool, str]:
    """
    Verify HMAC signature from CMS webhook.

    Returns:
        (is_valid, error_message)
    """
    config = get_config()
    secret = config.webhook_secret

    # Log all headers for debugging (remove in production)
    log.debug(f"Webhook headers: {dict(request.headers)}")

    # If secret is configured, signature is REQUIRED
    if secret:
        # Try multiple possible header names that Re:Earth CMS might use
        # Note: Re:Earth CMS uses "reearth-signature" (lowercase, no X- prefix)
        signature = (
            request.headers.get("reearth-signature") or
            request.headers.get("X-Reearth-Signature") or
            request.headers.get("X-Signature") or
            request.headers.get("X-Hub-Signature-256") or
            request.headers.get("X-Webhook-Signature") or
            ""
        )
        if not signature:
            # Log available headers to help debug
            sig_headers = [k for k in request.headers.keys() if 'sig' in k.lower() or 'auth' in k.lower()]
            log.warning(f"No signature header found. Available signature-related headers: {sig_headers}")
            log.warning(f"All headers: {list(request.headers.keys())}")
            return False, "Missing signature header"

        # Handle Re:Earth CMS signature format: v1,t=<timestamp>,<signature>
        if signature.startswith("v1,t="):
            try:
                parts = signature.split(",")
                timestamp = parts[1].split("=")[1]  # Extract timestamp from t=<timestamp>
                sig_hex = parts[2]  # The actual signature

                # Try with secret as string
                secret_str = secret.encode()
                # Also try decoding secret from hex (Re:Earth may use hex-encoded secrets)
                try:
                    secret_hex = bytes.fromhex(secret)
                except ValueError:
                    secret_hex = secret_str

                # Try multiple signing methods with both secret formats
                methods = []

                # String secret methods
                methods.append(("body (str)", hmac.new(secret_str, body, hashlib.sha256).hexdigest()))
                methods.append(("ts.body (str)", hmac.new(secret_str, f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()))

                # Hex-decoded secret methods
                methods.append(("body (hex)", hmac.new(secret_hex, body, hashlib.sha256).hexdigest()))
                methods.append(("ts.body (hex)", hmac.new(secret_hex, f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()))

                for method_name, expected in methods:
                    if hmac.compare_digest(sig_hex, expected):
                        log.info(f"Signature verified (method: {method_name})")
                        return True, ""

                # None matched - log debug info
                log.warning(f"Signature mismatch: received={sig_hex[:16]}...")
                for method_name, expected in methods:
                    log.warning(f"  Expected ({method_name}): {expected[:16]}...")
                return False, "Invalid signature"
            except (IndexError, ValueError) as e:
                log.warning(f"Failed to parse Re:Earth signature format: {e}")
                return False, "Invalid signature format"

        # Handle simple hex or prefixed signatures (e.g., "sha256=...")
        if signature.startswith("sha256="):
            signature = signature[7:]

        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        log.debug(f"Signature verification: received={signature[:16]}..., expected={expected[:16]}...")
        if not hmac.compare_digest(signature, expected):
            log.warning(f"Signature mismatch: received={signature}, expected={expected}")
            return False, "Invalid signature"

    return True, ""


def extract_model_id_from_payload(payload: dict) -> Optional[str]:
    """
    Extract model ID from webhook payload and map to config model ID.

    Re:Earth CMS webhook payload structure:
    {
        "type": "item.update",
        "data": {
            "item": {"modelId": "..."},
            "model": {"id": "...", "key": "public_facility"}
        }
    }

    Returns:
        Config model ID if found, None otherwise
    """
    data = payload.get('data', {})

    # Re:Earth CMS specific: model key is in data.model.key
    model_info = data.get('model', {})
    model_key = model_info.get('key')  # e.g., "public_facility"
    model_uuid = model_info.get('id')  # UUID like "01kbc2ah1a7r8b7d17tnkfrcct"

    # Also try item.modelId
    item_info = data.get('item', {})
    item_model_id = item_info.get('modelId')

    # Try to find a matching config model
    config = get_config()

    # First, try model key (most reliable for Re:Earth CMS)
    if model_key and model_key in config.models:
        log.info(f"Found model by key: {model_key}")
        return model_key

    # Try matching by webhook_model_keys (for CMS models with different keys)
    for config_model_id, model_config in config.models.items():
        if model_key and model_key in model_config.webhook_model_keys:
            log.info(f"Mapped webhook model key '{model_key}' to config model {config_model_id}")
            return config_model_id

    # Try matching by cms_model_id
    for config_model_id, model_config in config.models.items():
        cms_id = model_config.cms_model_id
        if cms_id in (model_key, model_uuid, item_model_id):
            log.info(f"Mapped CMS model {cms_id} to config model {config_model_id}")
            return config_model_id

    # Fallback: try other possible locations
    model_id = (
        data.get('modelId') or
        data.get('model_id') or
        data.get('modelKey') or
        payload.get('modelId') or
        payload.get('model_id')
    )

    if model_id:
        if model_id in config.models:
            return model_id
        for config_model_id, model_config in config.models.items():
            if model_config.cms_model_id == model_id:
                return config_model_id

    log.warning(f"Could not extract model ID. model_key={model_key}, model_uuid={model_uuid}")
    return None


def run_webhook_sync(model_id: str):
    """Background task to run sync for a model (triggered by webhook)"""
    with _sync_lock:
        service = get_service()
        if service._is_syncing:
            log.warning(f"Webhook sync skipped for {model_id} - already syncing")
            return

        try:
            log.info(f"Webhook triggered sync for model: {model_id}")
            service.sync_model_smart(model_id)
            log.info(f"Webhook sync completed for model: {model_id}")
        except Exception as e:
            log.error(f"Webhook sync failed for {model_id}: {e}")


def scheduled_sync_all():
    """Scheduled task to sync all models using smart mode"""
    with _sync_lock:
        log.info("Scheduled sync triggered")
        service = get_service()

        if service._is_syncing:
            log.warning("Skipping scheduled sync - already in progress")
            return

        # Sync all models with smart mode
        config = get_config()
        for model_id in config.get_all_model_ids():
            try:
                log.info(f"Scheduled sync: processing {model_id}")
                service.sync_model_smart(model_id)
            except Exception as e:
                log.error(f"Scheduled sync failed for {model_id}: {e}")

        log.info("Scheduled sync completed")


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    global _scheduler

    log.info("Starting CMS-CKAN Sync Web UI")
    try:
        config = get_config()
        errors = validate_config(config)
        if errors:
            log.error(f"Configuration errors: {errors}")
        else:
            log.info("Configuration validated successfully")

        # Initialize scheduler (only once per process)
        if _scheduler is None:
            # Use JST (Japan Standard Time) for 2:00 AM local time
            timezone = pytz.timezone('Asia/Tokyo')

            _scheduler = BackgroundScheduler(timezone=timezone)

            # Run daily at 2:00 AM JST
            _scheduler.add_job(
                scheduled_sync_all,
                CronTrigger(hour=2, minute=0, timezone=timezone),
                id="daily_sync",
                replace_existing=True,
                max_instances=1  # Prevent concurrent executions
            )

            _scheduler.start()
            log.info("Scheduled sync enabled: daily at 02:00 JST")
        else:
            log.warning("Scheduler already running, skipping initialization")

    except Exception as e:
        log.error(f"Startup error: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown scheduler gracefully"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("Scheduler stopped")


# ============== Webhook Endpoint (No Basic Auth) ==============

@app.get("/api/webhook/cms")
async def webhook_cms_verify():
    """
    Webhook verification endpoint.
    Some systems (like Re:Earth CMS) send a GET request first to verify the endpoint exists.
    """
    log.info("Webhook verification request received (GET)")
    return {
        "status": "ok",
        "message": "Webhook endpoint is active",
        "endpoint": "/api/webhook/cms",
        "method": "POST"
    }


@app.post("/api/webhook/cms", status_code=202)
async def webhook_cms_trigger(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint for CMS auto-sync.
    No Basic Auth required - uses HMAC signature verification.
    Returns 202 immediately, sync runs in background.
    """
    body = await request.body()

    # Verify signature (strict: 401 if secret configured but no/invalid signature)
    is_valid, error_msg = verify_webhook_signature(request, body)
    if not is_valid:
        log.warning(f"Webhook signature verification failed: {error_msg}")
        raise HTTPException(status_code=401, detail=error_msg)

    # Parse payload
    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    log.info(f"Webhook received: type={payload.get('type', 'unknown')}")

    # Extract model ID from payload
    model_id = extract_model_id_from_payload(payload)
    if not model_id:
        # Don't trigger sync_all - return 400
        raise HTTPException(
            status_code=400,
            detail="Could not extract model ID from payload"
        )

    # Check if already syncing
    service = get_service()
    if service._is_syncing:
        log.info(f"Webhook for {model_id}: sync already in progress, queued")
        return {
            "status": "queued",
            "message": "Sync already in progress, request queued",
            "model_id": model_id
        }

    # Run sync in background (non-blocking)
    background_tasks.add_task(run_webhook_sync, model_id)

    return {
        "status": "accepted",
        "message": "Sync triggered in background",
        "model_id": model_id
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user: str = Depends(verify_auth)
):
    """
    Main dashboard page.

    Shows:
    - Model configurations
    - Sync status
    - Recent history
    - Sync controls
    """
    service = get_service()
    config = get_config()

    status = service.get_status()
    history = service.get_history(limit=10)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "config": config,
        "status": status,
        "history": history,
        "now": datetime.now(),
        "active_tab": "history"
    })


@app.get("/settings", response_class=HTMLResponse, name="settings_page")
async def settings_page(
    request: Request,
    user: str = Depends(verify_auth)
):
    """Settings page for API configuration."""
    config = get_config()
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user": user,
        "config": config,
        "now": datetime.now(),
        "active_tab": "settings"
    })


@app.get("/sync", response_class=HTMLResponse, name="sync_page")
async def sync_page(
    request: Request,
    user: str = Depends(verify_auth)
):
    """New Sync page."""
    config = get_config()
    return templates.TemplateResponse("sync.html", {
        "request": request,
        "user": user,
        "config": config,
        "now": datetime.now(),
        "active_tab": "sync"
    })


@app.get("/jobs", response_class=HTMLResponse, name="jobs_page")
async def jobs_page(
    request: Request,
    user: str = Depends(verify_auth)
):
    """Saved Jobs page."""
    config = get_config()
    jobs = load_saved_jobs()
    return templates.TemplateResponse("jobs.html", {
        "request": request,
        "user": user,
        "config": config,
        "jobs": jobs,
        "now": datetime.now(),
        "active_tab": "jobs"
    })


# ============== Config API ==============

@app.get("/api/config")
async def get_api_config(user: str = Depends(verify_auth)):
    """Get current configuration (with masked tokens)."""
    config = get_config()
    return {
        "cms_url": config.cms_base_url,
        "cms_token_set": bool(config.cms_token),
        "ckan_url": config.ckan_url,
        "ckan_token_set": bool(config.ckan_token),
        "ckan_organization": config.ckan_organization
    }


@app.post("/api/config")
async def update_api_config(
    request: ConfigUpdateRequest,
    user: str = Depends(verify_auth)
):
    """Update API configuration."""
    global _config, _service

    try:
        # Load current runtime config
        current = load_runtime_config()

        # Update only provided fields
        if request.cms_url is not None:
            current["cms_url"] = request.cms_url
        if request.cms_token is not None:
            current["cms_token"] = request.cms_token
        if request.ckan_url is not None:
            current["ckan_url"] = request.ckan_url
        if request.ckan_token is not None:
            current["ckan_token"] = request.ckan_token
        if request.ckan_organization is not None:
            current["ckan_organization"] = request.ckan_organization

        # Save config
        save_runtime_config(current)

        # Reload config and service
        _config = None
        _service = None

        log.info(f"Configuration updated by user: {user}")
        return {"success": True, "message": "Configuration saved"}

    except Exception as e:
        log.error(f"Failed to save configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/test-cms")
async def test_cms_connection(
    request: ConnectionTestRequest,
    user: str = Depends(verify_auth)
):
    """Test CMS connection."""
    try:
        client = CMSClient(request.url, request.token)
        success = client.test_connection()
        return {
            "success": success,
            "message": "Connected successfully" if success else "Connection failed"
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/config/test-ckan")
async def test_ckan_connection(
    request: ConnectionTestRequest,
    user: str = Depends(verify_auth)
):
    """Test CKAN connection."""
    try:
        client = CKANClient(
            request.url,
            request.token or "",
            request.organization or ""
        )
        success = client.test_connection()
        return {
            "success": success,
            "message": "Connected successfully" if success else "Connection failed"
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============== CMS API ==============

@app.get("/api/cms/models")
async def list_cms_models(user: str = Depends(verify_auth)):
    """List configured CMS models."""
    config = get_config()
    models = []
    for model_id, model_config in config.models.items():
        models.append({
            "id": model_id,
            "cms_model_id": model_config.cms_model_id,
            "title": model_config.ckan_dataset.title,
            "geometry_field": model_config.geometry_field
        })
    return {"models": models}


@app.get("/api/cms/models/{model_id}/preview")
async def preview_cms_model(
    model_id: str,
    limit: int = Query(default=5, le=20),
    user: str = Depends(verify_auth)
):
    """Preview data from a CMS model."""
    config = get_config()
    try:
        client = CMSClient(config.cms_base_url, config.cms_token)
        data = client.fetch_model_items(model_id, page=1, per_page=limit)

        # Extract items and fields
        items = data.get("results", data) if isinstance(data, dict) else data
        if isinstance(items, list) and len(items) > 0:
            fields = list(items[0].keys()) if items else []
        else:
            fields = []
            items = []

        total_count = data.get("totalCount", len(items)) if isinstance(data, dict) else len(items)

        return {
            "total_count": total_count,
            "fields": fields,
            "records": items[:limit]
        }
    except Exception as e:
        return {"error": str(e), "records": [], "total_count": 0}


@app.get("/api/cms/models/{model_id}/fields")
async def get_cms_model_fields(
    model_id: str,
    user: str = Depends(verify_auth)
):
    """Get fields from a CMS model by sampling data."""
    config = get_config()
    try:
        client = CMSClient(config.cms_base_url, config.cms_token)
        data = client.fetch_model_items(model_id, page=1, per_page=1)

        items = data.get("results", data) if isinstance(data, dict) else data
        if isinstance(items, list) and len(items) > 0:
            fields = list(items[0].keys())
        else:
            fields = []

        total_count = data.get("totalCount", len(items)) if isinstance(data, dict) else len(items)

        return {"fields": fields, "total_count": total_count}
    except Exception as e:
        return {"error": str(e), "fields": [], "total_count": 0}


# ============== CKAN API ==============

@app.get("/api/ckan/datasets")
async def list_ckan_datasets(user: str = Depends(verify_auth)):
    """List CKAN datasets in the configured organization."""
    config = get_config()
    try:
        client = CKANClient(
            config.ckan_url,
            config.ckan_token,
            config.ckan_organization
        )
        datasets = client.list_datasets(config.ckan_organization)
        return {
            "datasets": [
                {
                    "id": d.get("id"),
                    "name": d.get("name"),
                    "title": d.get("title"),
                    "num_resources": d.get("num_resources", 0)
                }
                for d in datasets
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/ckan/datasets/{dataset_id}/resources")
async def list_ckan_resources(
    dataset_id: str,
    user: str = Depends(verify_auth)
):
    """List resources in a CKAN dataset."""
    config = get_config()
    try:
        client = CKANClient(
            config.ckan_url,
            config.ckan_token,
            config.ckan_organization
        )
        resources = client.get_dataset_resources(dataset_id)
        return {
            "resources": [
                {
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "format": r.get("format"),
                    "size": r.get("size"),
                    "created": r.get("created")
                }
                for r in resources
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/ckan/resources")
async def list_all_ckan_resources(user: str = Depends(verify_auth)):
    """List all resources from all datasets in the organization."""
    config = get_config()
    try:
        client = CKANClient(
            config.ckan_url,
            config.ckan_token,
            config.ckan_organization
        )
        datasets = client.list_datasets(config.ckan_organization)
        all_resources = []

        for dataset in datasets:
            dataset_id = dataset.get("name") or dataset.get("id")
            dataset_title = dataset.get("title", dataset_id)
            try:
                resources = client.get_dataset_resources(dataset_id)
                for r in resources:
                    all_resources.append({
                        "id": r.get("id"),
                        "name": r.get("name"),
                        "format": r.get("format"),
                        "dataset_id": dataset_id,
                        "dataset_title": dataset_title,
                        "size": r.get("size"),
                        "created": r.get("created")
                    })
            except Exception:
                continue

        return {"resources": all_resources}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============== Jobs API ==============

def get_jobs_file() -> Path:
    """Get path to saved jobs file."""
    config = get_config()
    data_dir = Path(config.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "saved_jobs.json"


def load_saved_jobs() -> List[dict]:
    """Load saved jobs from file."""
    jobs_file = get_jobs_file()
    if jobs_file.exists():
        try:
            with open(jobs_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_jobs(jobs: List[dict]) -> None:
    """Save jobs to file."""
    jobs_file = get_jobs_file()
    with open(jobs_file, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, indent=2, default=str)


@app.get("/api/jobs")
async def list_jobs(user: str = Depends(verify_auth)):
    """List saved sync jobs."""
    return {"jobs": load_saved_jobs()}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str, user: str = Depends(verify_auth)):
    """Get a single job by ID."""
    jobs = load_saved_jobs()
    for job in jobs:
        if job["job_id"] == job_id:
            return job
    raise HTTPException(status_code=404, detail="Job not found")


@app.post("/api/jobs")
async def create_job(
    job: SavedJob,
    user: str = Depends(verify_auth)
):
    """Create a new saved job."""
    jobs = load_saved_jobs()

    new_job = {
        "job_id": str(uuid.uuid4()),
        "name": job.name,
        "config": job.config.model_dump(),
        "created_at": datetime.now().isoformat(),
        "last_run": None
    }
    jobs.append(new_job)
    save_jobs(jobs)

    return {"success": True, "job": new_job}


@app.put("/api/jobs/{job_id}")
async def update_job(
    job_id: str,
    job: SavedJob,
    user: str = Depends(verify_auth)
):
    """Update a saved job."""
    jobs = load_saved_jobs()

    for i, j in enumerate(jobs):
        if j["job_id"] == job_id:
            jobs[i]["name"] = job.name
            jobs[i]["config"] = job.config.model_dump()
            save_jobs(jobs)
            return {"success": True, "job": jobs[i]}

    raise HTTPException(status_code=404, detail="Job not found")


@app.delete("/api/jobs/{job_id}")
async def delete_job(
    job_id: str,
    user: str = Depends(verify_auth)
):
    """Delete a saved job."""
    jobs = load_saved_jobs()
    jobs = [j for j in jobs if j["job_id"] != job_id]
    save_jobs(jobs)
    return {"success": True}


@app.post("/api/jobs/{job_id}/run")
async def run_job(
    job_id: str,
    user: str = Depends(verify_auth)
):
    """Run a saved job."""
    jobs = load_saved_jobs()

    job = None
    for j in jobs:
        if j["job_id"] == job_id:
            job = j
            break

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update last_run
    job["last_run"] = datetime.now().isoformat()
    save_jobs(jobs)

    # Execute the sync
    config_data = job["config"]
    flex_request = FlexSyncRequest(**config_data)

    service = get_service()
    result = service.sync_flexible(flex_request)

    return {
        "success": result.status == SyncStatusEnum.SUCCESS,
        "result": result.to_dict()
    }


@app.post("/api/sync", response_model=SyncResponse)
async def trigger_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    user: str = Depends(verify_auth)
):
    """
    Trigger sync via API.

    Args:
        request: Sync request parameters
        background_tasks: FastAPI background tasks
        user: Authenticated user

    Returns:
        Sync results
    """
    service = get_service()

    # Check if already syncing
    if service._is_syncing:
        raise HTTPException(
            status_code=409,
            detail="Sync already in progress"
        )

    log.info(f"Sync triggered by user: {user} (models={request.models}, sync_mode={request.sync_mode}, resource_id={request.resource_id})")

    # Handle update mode
    if request.sync_mode == "update" and request.resource_id:
        # Update specific resource by ID
        results = service.sync_all(
            model_ids=request.models,
            dry_run=request.dry_run,
            force=request.force,
            update_resource_id=request.resource_id
        )
    else:
        # Default: use smart sync to update existing resources or create new ones
        # This prevents duplicate resources from being created
        results = []
        model_ids = request.models or config.get_all_model_ids()
        for model_id in model_ids:
            if request.dry_run:
                # Dry run uses sync_all for detailed preview
                result = service.sync_model(model_id, dry_run=True)
            elif request.force:
                # Force mode uses sync_all to delete and recreate
                result = service.sync_model(model_id, force=True)
            else:
                # Smart sync: update existing or create new
                result = service.sync_model_smart(model_id)
            results.append(result)

    # Prepare response
    success = all(r.status == SyncStatusEnum.SUCCESS for r in results)
    failed_count = sum(1 for r in results if r.status == SyncStatusEnum.FAILED)

    if request.sync_mode == "update":
        message = f"Update completed: {len(results) - failed_count}/{len(results)} successful"
    else:
        message = f"Sync completed: {len(results) - failed_count}/{len(results)} successful"

    if request.dry_run:
        message = f"Dry run completed: {len(results)} models processed"

    return SyncResponse(
        success=success,
        message=message,
        results=[r.to_dict() for r in results]
    )


@app.post("/api/sync/flexible")
async def trigger_flexible_sync(
    request: FlexSyncRequest,
    user: str = Depends(verify_auth)
):
    """
    Trigger flexible sync with custom source/target configuration.

    Args:
        request: Flexible sync request parameters
        user: Authenticated user

    Returns:
        Sync result
    """
    service = get_service()

    # Check if already syncing
    if service._is_syncing:
        raise HTTPException(
            status_code=409,
            detail="Sync already in progress"
        )

    log.info(f"Flexible sync triggered by user: {user} (model={request.cms_model_id}, target={request.target_mode})")

    try:
        result = service.sync_flexible(request)

        return {
            "success": result.status == SyncStatusEnum.SUCCESS,
            "message": f"Sync {'completed' if result.status == SyncStatusEnum.SUCCESS else 'failed'}",
            "result": result.to_dict()
        }
    except Exception as e:
        log.error(f"Flexible sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status(user: str = Depends(verify_auth)):
    """
    Get current sync status.

    Returns:
        Current status as JSON
    """
    service = get_service()
    status = service.get_status()
    return status.to_dict()


@app.get("/api/history")
async def get_history(
    limit: int = Query(default=20, le=100),
    user: str = Depends(verify_auth)
):
    """
    Get sync history.

    Args:
        limit: Maximum number of entries to return

    Returns:
        List of sync results
    """
    service = get_service()
    history = service.get_history(limit=limit)
    return [r.to_dict() for r in history]


@app.get("/api/models")
async def get_models(user: str = Depends(verify_auth)):
    """
    Get configured models.

    Returns:
        List of model configurations
    """
    config = get_config()
    return {
        model_id: {
            "cms_model_id": model_config.cms_model_id,
            "ckan_dataset": {
                "name": model_config.ckan_dataset.name,
                "title": model_config.ckan_dataset.title
            },
            "geometry_field": model_config.geometry_field
        }
        for model_id, model_config in config.models.items()
    }


@app.get("/api/test")
async def test_connections(user: str = Depends(verify_auth)):
    """
    Test connections to CMS and CKAN.

    Returns:
        Connection status for each service
    """
    service = get_service()
    return service.test_connections()


@app.get("/health")
async def health_check():
    """
    Health check endpoint (no auth required).

    Returns:
        Service health status
    """
    try:
        service = get_service()
        return {
            "status": "healthy",
            "is_syncing": service._is_syncing,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


# Run with uvicorn if executed directly
if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run(
        "app:app",
        host=config.web_host,
        port=config.web_port,
        reload=True
    )
