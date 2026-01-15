# CMS-CKAN Sync Service

A synchronization service that transfers data from Re:Earth CMS to CKAN open data platform.

## Features

- **Data Sync**: Automatically fetch data from Re:Earth CMS and upload to CKAN
- **Format Support**: Export data as CSV and GeoJSON
- **CLI & Web UI**: Both command-line and web dashboard interfaces
- **Dry Run Mode**: Preview changes without uploading
- **Force Mode**: Delete existing resources before re-uploading
- **History Tracking**: View past sync results
- **Docker Support**: Easy deployment with Docker Compose

## Architecture

```
Re:Earth CMS (Integration API) → Sync Service → CKAN (Action API)
                                      ↓
                               Transform: JSON → CSV/GeoJSON
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (optional)
- Re:Earth CMS Integration Token
- CKAN API Token with write access

### Installation

1. Clone or copy the project:
```bash
cd /home/ubuntu/cms-ckan-sync
```

2. Create environment file:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Configuration

Edit `.env` with your credentials:
```bash
# CMS Configuration
CMS_API_BASE_URL=https://api.cms.reearth.io/api/p/YOUR_PROJECT_ID
CMS_API_TOKEN=your-cms-integration-token

# CKAN Configuration
CKAN_URL=https://your-ckan-instance.org
CKAN_API_TOKEN=your-ckan-api-token
CKAN_ORGANIZATION=your-organization-id

# Web UI Configuration
WEB_HOST=0.0.0.0
WEB_PORT=8080
WEB_AUTH_USERNAME=admin
WEB_AUTH_PASSWORD=your-secure-password

# General
LOG_LEVEL=INFO
DATA_DIR=./data
```

Edit `config/models.yaml` to define your models:
```yaml
models:
  public_facility:
    cms_model_id: public_facility
    ckan_dataset:
      name: public-facilities
      title: "Public Facilities"
      notes: "Public facility data from CMS"
      tags:
        - name: public-facility
        - name: infrastructure
    geometry_field: location  # Optional, for GeoJSON export
```

## Usage

### CLI Mode

```bash
# Sync all models
python -m cli.main

# Sync specific models
python -m cli.main --models public_facility

# Dry run (preview without uploading)
python -m cli.main --dry-run

# Force re-upload
python -m cli.main --force

# Output as JSON
python -m cli.main --json

# Test connections
python -m cli.main --test

# Show status
python -m cli.main --status

# Show history
python -m cli.main --history 10
```

### Web UI Mode

```bash
# Start web server
python -m uvicorn web.app:app --host 0.0.0.0 --port 8080

# Or with Docker
docker compose up -d cms-sync-web
```

Access the dashboard at: http://localhost:8080

### Docker Commands

```bash
# Build images
docker compose build

# Run CLI sync
docker compose --profile cli run --rm cms-sync-cli

# Run with specific options
docker compose --profile cli run --rm cms-sync-cli --models public_facility --dry-run

# Start Web UI (runs continuously)
docker compose up -d cms-sync-web

# View Web UI logs
docker compose logs -f cms-sync-web

# Stop Web UI
docker compose down
```

### Cron Setup

Add to crontab for automatic sync:
```bash
# Run daily at 2 AM
0 2 * * * cd /home/ubuntu/cms-ckan-sync && python -m cli.main >> /var/log/cms-sync.log 2>&1

# Or with Docker
0 2 * * * cd /home/ubuntu/cms-ckan-sync && docker compose --profile cli run --rm cms-sync-cli >> /var/log/cms-sync.log 2>&1
```

## API Endpoints (Web UI)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard (HTML) |
| `/api/sync` | POST | Trigger sync |
| `/api/status` | GET | Get current status |
| `/api/history` | GET | Get sync history |
| `/api/models` | GET | List configured models |
| `/api/test` | GET | Test connections |
| `/api/webhook/cms` | GET/POST | Webhook for Re:Earth CMS auto-sync |
| `/health` | GET | Health check (no auth) |

For complete API documentation including webhook setup, see [docs/api.md](docs/api.md).

### Sync API Example

```bash
curl -X POST http://localhost:8080/api/sync \
  -u admin:your-password \
  -H "Content-Type: application/json" \
  -d '{"models": ["public_facility"], "dry_run": false, "force": false}'
```

## Project Structure

```
cms-ckan-sync/
├── config/
│   └── models.yaml          # Model configurations
├── sync_service/            # Core business logic
│   ├── config.py            # Configuration loader
│   ├── core.py              # SyncService class
│   ├── cms_client.py        # CMS API client
│   ├── ckan_client.py       # CKAN API client
│   ├── transformers.py      # Data transformers
│   ├── models.py            # Data models
│   └── logger.py            # Logging setup
├── cli/
│   └── main.py              # CLI entry point
├── web/
│   ├── app.py               # FastAPI application
│   ├── templates/           # HTML templates
│   └── static/              # CSS/JS files
├── data/
│   └── sync_history.json    # Sync history
├── tests/                   # Unit tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Troubleshooting

### Connection Errors

1. **CMS Authentication Failed**
   - Verify `CMS_API_TOKEN` is correct
   - Check token hasn't expired

2. **CKAN API Error**
   - Verify `CKAN_API_TOKEN` has write permissions
   - Ensure organization exists

3. **Network Timeout**
   - Check firewall rules
   - Verify URLs are accessible

### Common Issues

**No data in CKAN after sync:**
- Check `--dry-run` is not enabled
- Verify CKAN organization ID is correct
- Check CLI output for errors

**GeoJSON not generated:**
- Ensure `geometry_field` is configured in models.yaml
- Verify data contains valid geometry

**Web UI not accessible:**
- Check port binding (default 8080)
- Verify credentials in `.env`

### Logs

```bash
# View CLI logs
tail -f /var/log/cms-sync.log

# View Docker logs
docker compose logs -f cms-sync-web

# Increase log verbosity
LOG_LEVEL=DEBUG python -m cli.main
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

### Adding New Models

1. Add model configuration to `config/models.yaml`
2. Test with `--dry-run` first
3. Run full sync

## Security Notes

- Store API tokens securely (use environment variables)
- Web UI uses Basic Auth - use HTTPS in production
- Consider VPC/IP restrictions for dashboard access
- Regularly rotate API tokens

## License

MIT License
