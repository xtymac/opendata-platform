# CMS-CKAN Sync Service Documentation

## Overview

The CMS-CKAN Sync Service automatically synchronizes data from Re:Earth CMS to CKAN Open Data Portal. When content is published in CMS, a webhook triggers automatic data sync to CKAN within 1-2 seconds.

## Architecture

```
┌─────────────────┐     Webhook      ┌──────────────────┐     API      ┌─────────────┐
│   Re:Earth CMS  │ ───────────────► │  cms-sync-web    │ ───────────► │    CKAN     │
│                 │   (on publish)   │  (Docker)        │              │             │
└─────────────────┘                  └──────────────────┘              └─────────────┘
                                              │                               │
                                              │                               ▼
                                              │                        ┌─────────────┐
                                              └──────────────────────► │ DataPusher  │
                                                  (trigger indexing)   └─────────────┘
```

## Components

| Component | URL | Description |
|-----------|-----|-------------|
| Re:Earth CMS | https://cms.reearth.io | Content Management System |
| cms-sync-web | Container: `cms-sync-web` | Webhook receiver & sync service |
| CKAN | https://opendata.uixai.org | Open Data Portal |
| DataPusher | Container: `ckan-datapusher` | Auto-indexes CSV data for API access |

## Configuration Files

### 1. Environment Variables (`/home/ubuntu/cms-ckan-sync/.env`)

```bash
# CMS Configuration
CMS_API_BASE_URL=https://api.cms.reearth.io/api/p/eukarya/open-data-template
CMS_API_TOKEN=                    # Optional for public projects

# CKAN Configuration
CKAN_URL=https://opendata.uixai.org
CKAN_API_TOKEN=<your-ckan-api-token>
CKAN_ORGANIZATION=open-data-template

# Web Service
WEB_HOST=0.0.0.0
WEB_PORT=8080

# Webhook Secret (optional - for HMAC verification)
WEBHOOK_SECRET=
```

### 2. Model Mappings (`/home/ubuntu/cms-ckan-sync/config/models.yaml`)

```yaml
models:
  public_facility:                    # Internal model ID
    cms_model_id: public_facility     # CMS model identifier for API
    webhook_model_keys:               # Model keys sent in webhook payload
      - facilities-for-citizens       # Must match CMS model key exactly
    ckan_dataset:
      name: public-facilities         # CKAN dataset URL slug
      title: "Public Facilities"
      notes: |
        Public facility data synchronized from Re:Earth CMS.
      license_id: cc-by
      tags:
        - name: public-facility
        - name: cms-sync
    field_mappings: {}                # Optional field transformations
    geometry_field: location          # GeoJSON field name
    exclude_fields:
      - __reearth_metadata            # Fields to exclude from sync
```

## Webhook Configuration (CMS Side)

### Settings in Re:Earth CMS

| Setting | Value |
|---------|-------|
| **Name** | CKAN Auto Sync |
| **URL** | `https://opendata.uixai.org/sync/api/webhook/cms` |
| **Secret** | `e5151cbd6b63880b0c2389158d3194e81bb3371d5784c7723dc6fbe3ef99ed15` |
| **Trigger Events** | Create, Update, Delete, Publish |

### How to Configure

1. Go to CMS → Project Settings → Integrations → Webhook
2. Create new webhook with above settings
3. Enable desired trigger events (Publish is most important)
4. Save

## Data Flow

### Automatic Sync (Webhook)

```
1. User edits content in CMS
2. User clicks "Publish"
3. CMS sends POST to webhook URL with payload:
   {
     "type": "item.publish",
     "data": {
       "item": { ... },
       "model": {
         "key": "facilities-for-citizens",  ← This must match webhook_model_keys
         "id": "01k8x8s41rej43hag5vws8ttdc"
       }
     }
   }
4. cms-sync-web receives webhook
5. Matches model.key to configured webhook_model_keys
6. Fetches ALL data from CMS Public API
7. Transforms to CSV format
8. Uploads to CKAN dataset
9. Triggers DataPusher for indexing
10. Data available in CKAN (~1-2 seconds total)
```

### Manual Sync (Dashboard)

1. Go to https://opendata.uixai.org/sync/
2. Login with credentials (admin / cms-sync-admin-2024)
3. Select model and click "Sync Now"

## Adding a New Model

### Step 1: Identify CMS Model Key

Check the webhook logs to find the `model_key` being sent:
```bash
docker logs cms-sync-web 2>&1 | grep "model_key="
```

### Step 2: Add to models.yaml

```yaml
models:
  # ... existing models ...

  new_model:
    cms_model_id: new_model           # For CMS API calls
    webhook_model_keys:
      - actual-cms-model-key          # From webhook payload
    ckan_dataset:
      name: new-model-dataset
      title: "New Model Dataset"
      notes: "Description here"
      license_id: cc-by
      tags:
        - name: new-tag
    field_mappings: {}
    geometry_field: location          # or null if no geometry
    exclude_fields:
      - __reearth_metadata
```

### Step 3: Restart Service

```bash
docker restart cms-sync-web
```

### Step 4: Test

Publish something in CMS and check logs:
```bash
docker logs --tail 50 cms-sync-web
```

## Monitoring & Troubleshooting

### Check Service Status

```bash
# Container status
docker ps | grep cms-sync

# Recent logs
docker logs --tail 100 cms-sync-web

# Webhook activity only
docker logs cms-sync-web 2>&1 | grep -E "Webhook|POST.*webhook"
```

### Check Sync History

```bash
docker exec cms-sync-web cat /app/data/sync_history.json | python3 -m json.tool | tail -50
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `400 Bad Request` | Model key not configured | Add model key to `webhook_model_keys` in models.yaml |
| `Could not extract model ID` | Missing model mapping | Add model to models.yaml |
| No webhook received | Webhook not configured in CMS | Check CMS webhook settings |
| Data not in CKAN | DataPusher failed | Check `docker logs ckan-datapusher` |

### Debug Webhook Payload

To see full webhook payload, temporarily increase log level:
```bash
# In .env
LOG_LEVEL=DEBUG
```

Then restart and check logs.

## File Locations

| File | Path | Purpose |
|------|------|---------|
| Environment config | `/home/ubuntu/cms-ckan-sync/.env` | API keys, URLs |
| Model mappings | `/home/ubuntu/cms-ckan-sync/config/models.yaml` | Model configurations |
| Sync history | `/home/ubuntu/cms-ckan-sync/data/sync_history.json` | Sync records |
| Sync logs | `/home/ubuntu/cms-ckan-sync/data/sync_*.log` | Daily log files |

## Docker Commands

```bash
# Start service
cd /home/ubuntu/cms-ckan-sync
docker-compose up -d

# Stop service
docker-compose down

# Restart after config change
docker restart cms-sync-web

# View logs
docker logs -f cms-sync-web

# Enter container
docker exec -it cms-sync-web bash
```

## Performance

| Metric | Value |
|--------|-------|
| Webhook to sync complete | ~1-2 seconds |
| Records per sync | Full dataset (incremental not supported) |
| DataPusher indexing | ~0.5 seconds for small datasets |

## Security

- Webhook endpoint is public but can verify HMAC signature
- CKAN API token stored in `.env` (not in repo)
- Dashboard protected by Basic Auth
- HTTPS for all external communications

## Current Model Mappings

| CMS Model | Webhook Key | CKAN Dataset |
|-----------|-------------|--------------|
| public_facility | facilities-for-citizens | public-facilities |
| childcare_facilities | childcare_facilities, childcare | childcare-facilities |

---

*Last updated: 2025-12-17*
