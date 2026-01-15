# CMS-CKAN Sync API Documentation

## Overview

| Item | Value |
|------|-------|
| Base URL | `http://localhost:8080` |
| Default Auth | Basic Authentication |
| Content-Type | `application/json` |

## Authentication

### Basic Auth
Most endpoints require Basic Authentication:
```bash
curl -u username:password http://localhost:8080/api/status
```

Credentials are configured in `.env`:
```bash
WEB_AUTH_USERNAME=admin
WEB_AUTH_PASSWORD=your-secure-password
```

### HMAC Signature (Webhook only)
Webhook endpoint uses HMAC-SHA256 signature verification instead of Basic Auth.

---

## Endpoints Summary

### General Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Health check |
| `/` | GET | Basic | Dashboard (HTML) |
| `/api/status` | GET | Basic | Current sync status |
| `/api/history` | GET | Basic | Sync history |
| `/api/models` | GET | Basic | List configured models |
| `/api/test` | GET | Basic | Test CMS/CKAN connections |
| `/api/sync` | POST | Basic | Manual sync trigger |

### Webhook Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/webhook/cms` | GET | None | Webhook verification |
| `/api/webhook/cms` | POST | HMAC | Auto-sync trigger from Re:Earth CMS |

---

## Endpoint Details

### GET /health

Health check endpoint (no authentication required).

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### GET /api/status

Get current sync status.

**Response:**
```json
{
  "is_syncing": false,
  "current_model": null,
  "last_sync": "2024-01-15T10:00:00Z"
}
```

---

### GET /api/history

Get sync history.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 10 | Number of records to return |

**Example:**
```bash
curl -u admin:password "http://localhost:8080/api/history?limit=5"
```

**Response:**
```json
{
  "history": [
    {
      "timestamp": "2024-01-15T10:00:00Z",
      "model": "public_facility",
      "status": "success",
      "records": 150,
      "duration": 12.5
    }
  ]
}
```

---

### GET /api/models

List all configured models.

**Response:**
```json
{
  "models": ["public_facility", "childcare_facility"]
}
```

---

### GET /api/test

Test connections to CMS and CKAN.

**Response:**
```json
{
  "cms": {
    "status": "ok",
    "url": "https://api.cms.reearth.io/api/p/..."
  },
  "ckan": {
    "status": "ok",
    "url": "https://your-ckan.org"
  }
}
```

---

### POST /api/sync

Manually trigger data synchronization.

**Request Body:**
```json
{
  "models": ["public_facility"],
  "dry_run": false,
  "force": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `models` | array | No | Models to sync (empty = all) |
| `dry_run` | bool | No | Preview without uploading |
| `force` | bool | No | Delete existing before upload |

**Example:**
```bash
curl -X POST http://localhost:8080/api/sync \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"models": ["public_facility"], "dry_run": false}'
```

**Response:**
```json
{
  "status": "started",
  "models": ["public_facility"],
  "dry_run": false
}
```

---

## Webhook API

### Overview

Re:Earth CMS can automatically trigger sync when content changes via webhook.

**Key Features:**
- No Basic Auth required
- Uses HMAC-SHA256 signature verification
- Returns 202 immediately, sync runs in background
- Prevents duplicate syncs with locking mechanism

---

### GET /api/webhook/cms

Verification endpoint for webhook handshake.

**Purpose:** Some systems send GET request first to verify endpoint exists.

**Response:**
```json
{
  "status": "ok",
  "message": "Webhook endpoint is active",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### POST /api/webhook/cms

Trigger sync from Re:Earth CMS webhook.

**Headers:**
| Header | Required | Description |
|--------|----------|-------------|
| `reearth-signature` | Conditional | HMAC signature (required if `WEBHOOK_SECRET` is set) |
| `Content-Type` | Yes | `application/json` |

**Signature Format:**
```
reearth-signature: v1,t=1705312200,abc123def456...
```

Format: `v1,t=<timestamp>,<hmac-sha256-hex>`

**Request Body (from Re:Earth CMS):**
```json
{
  "type": "item.update",
  "data": {
    "item": {
      "id": "item-uuid",
      "modelId": "model-uuid"
    },
    "model": {
      "id": "01kbc2ah1a7r8b7d17tnkfrcct",
      "key": "public_facility"
    }
  }
}
```

**Response Codes:**

| Code | Status | Description |
|------|--------|-------------|
| 202 | Accepted | Sync triggered in background |
| 400 | Bad Request | Invalid payload or model not found |
| 401 | Unauthorized | Invalid/missing signature |

**Success Response (202):**
```json
{
  "status": "accepted",
  "message": "Sync triggered in background",
  "model_id": "public_facility"
}
```

**Queued Response (202):**
```json
{
  "status": "queued",
  "message": "Sync already in progress, request queued",
  "model_id": "public_facility"
}
```

**Error Response (400):**
```json
{
  "detail": "Could not extract model ID from payload"
}
```

**Error Response (401):**
```json
{
  "detail": "Missing signature header"
}
```

---

## Webhook Configuration

### 1. Environment Variables

In `.env`:
```bash
# Webhook secret for HMAC signature verification
# Generate with: openssl rand -hex 32
WEBHOOK_SECRET=your-webhook-secret-minimum-32-characters
```

**Note:** If `WEBHOOK_SECRET` is empty, signature verification is disabled.

### 2. Model Configuration

In `config/models.yaml`, add `webhook_model_keys` to map CMS model keys:

```yaml
models:
  public_facility:
    cms_model_id: public_facility
    webhook_model_keys:
      - that              # model.key value in CMS webhook payload
      - public_facility   # alternative key
    ckan_dataset:
      name: public-facilities
      title: "Public Facilities"
```

### 3. Re:Earth CMS Setup

1. Go to Re:Earth CMS Project Settings → Webhooks
2. Add new webhook:
   - **URL:** `https://your-domain.com/api/webhook/cms`
   - **Secret:** Same value as `WEBHOOK_SECRET`
   - **Events:** Select item create/update/delete

---

## Error Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 202 | Accepted (async processing started) |
| 400 | Bad Request (invalid input) |
| 401 | Unauthorized (auth failed) |
| 500 | Internal Server Error |

---

## Testing with cURL

### Test webhook (no signature):
```bash
curl -X POST http://localhost:8080/api/webhook/cms \
  -H "Content-Type: application/json" \
  -d '{
    "type": "item.update",
    "data": {
      "model": {
        "id": "01kbc2ah1a7r8b7d17tnkfrcct",
        "key": "public_facility"
      }
    }
  }'
```

### Test manual sync:
```bash
curl -X POST http://localhost:8080/api/sync \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"models": ["public_facility"]}'
```

### Check status:
```bash
curl -u admin:password http://localhost:8080/api/status
```
