# PLATEAU Mock API

Simple Nginx-based mock API for testing the PLATEAU harvester.

## 🚀 Quick Start

```bash
# Start the mock API
docker-compose up -d

# Check it's running
curl http://localhost:8088/health

# List datasets
curl http://localhost:8088/api/v1/datasets

# Get dataset detail
curl http://localhost:8088/api/v1/datasets/13100_tokyo_chiyoda_2023
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/datasets` | GET | List all datasets (paginated) |
| `/api/v1/datasets/{id}` | GET | Get dataset detail by ID |

## 📝 Sample Dataset IDs

- `13100_tokyo_chiyoda_2023` - 東京都千代田区 (CityGML)
- `27100_osaka_kita_2023` - 大阪府大阪市北区 (3D Tiles)
- `14100_kanagawa_yokohama_2022` - 神奈川県横浜市 (CityGML + GeoJSON)

## 🔌 Connect to CKAN

### If CKAN is on host machine

Use `http://localhost:8088` in harvest config.

### If CKAN is in Docker

1. **Same compose file**: Add CKAN to this `docker-compose.yml`

2. **Separate compose files**: Use external network

```yaml
# In this docker-compose.yml
networks:
  plateau-network:
    external: true
    name: ckan_default  # Your CKAN network name
```

Then use `http://mockapi:8088` in harvest config.

## 🛑 Stop

```bash
docker-compose down
```

## 📊 Adding More Data

Add files to `data/` directory:

```bash
# List endpoint (required)
data/datasets.json

# Detail endpoints (one per dataset)
data/dataset_{id}.json
```

Format for `datasets.json`:
```json
{
  "results": [
    {"id": "...", "title": "...", ...}
  ]
}
```
