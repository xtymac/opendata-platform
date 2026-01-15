# ckanext-plateau-harvester

CKAN Harvester plugin for collecting PLATEAU (3D都市モデル / 3D City Model) datasets from REST or GraphQL APIs.

## 📋 Overview

This plugin enables CKAN to harvest metadata from PLATEAU-compatible APIs and create corresponding datasets with resources. It supports:

- ✅ REST API with pagination
- ✅ GraphQL API with cursor-based pagination
- ✅ Configurable field mapping
- ✅ Three-stage harvest process (gather/fetch/import)
- ✅ Incremental updates (create/update packages)

## 📁 Directory Structure

```
ckanext-plateau-harvester/
├── setup.py
├── README.md
├── requirements.txt
├── ckanext/
│   └── plateau_harvester/
│       ├── __init__.py
│       ├── plugin.py          # CKAN plugin entry point
│       ├── harvester.py       # Main harvester logic (gather/fetch/import)
│       ├── mapping.py         # API → CKAN package mapping
│       ├── http.py            # HTTP client (REST/GraphQL)
│       └── schemas/
│           └── sample_source_config.json
├── mockapi/                   # Mock API for testing
│   ├── docker-compose.yml
│   ├── nginx.conf
│   └── data/
│       ├── datasets.json
│       ├── dataset_001.json
│       └── dataset_002.json
└── tests/
```

## 🚀 Installation

### Prerequisites

- CKAN 2.10 or 2.11
- Python 3.9+
- `ckanext-harvest` installed and configured

### Option 1: Install from source

```bash
# Clone or copy this directory
cd /path/to/ckanext-plateau-harvester

# Install in development mode
pip install -e .

# Or install dependencies separately
pip install -r requirements.txt
```

### Option 2: Docker (ckan-docker)

Add to your Dockerfile:

```dockerfile
# Install ckanext-harvest first (if not already installed)
RUN pip install ckanext-harvest

# Copy and install plateau harvester
COPY ./ckanext-plateau-harvester /srv/app/src/ckanext-plateau-harvester
RUN pip install -e /srv/app/src/ckanext-plateau-harvester
```

### Enable the plugin

Edit your `ckan.ini`:

```ini
ckan.plugins = ... harvest plateau_harvester
```

Restart CKAN:

```bash
# Docker
docker-compose restart ckan

# Source install
sudo systemctl restart supervisord  # or your process manager
```

### Initialize harvest tables

If not already done for ckanext-harvest:

```bash
ckan -c /etc/ckan/ckan.ini db init  # Core CKAN
ckan -c /etc/ckan/ckan.ini harvester initdb  # Harvest extension
```

## 🧪 Quick Test with Mock API

### 1. Start the Mock API

The `mockapi/` directory contains a simple Nginx-based mock API serving sample PLATEAU data:

```bash
cd mockapi
docker-compose up -d
```

This starts a mock API at `http://localhost:8088` with endpoints:

- `GET /api/v1/datasets` - List all datasets (paginated)
- `GET /api/v1/datasets/{id}` - Get dataset detail

### 2. Create Harvest Source

#### Option A: Web UI

1. Navigate to: `http://your-ckan/harvest`
2. Click **"Add Harvest Source"**
3. Fill in:
   - **URL**: `http://localhost:8088/api/v1/` (placeholder, actual URL in config)
   - **Title**: `PLATEAU Mock API`
   - **Source type**: Select `PLATEAU / 3D都市モデル`
   - **Configuration**: Paste the following JSON:

```json
{
  "api_base": "http://mockapi:8088/api/v1/",
  "mode": "rest",
  "list_path": "datasets",
  "detail_path": "datasets/{id}",
  "page_size": 10,
  "owner_org": "plateau-data"
}
```

**Note**: Use `http://mockapi:8088` if CKAN is in Docker and connected to the same network. Use `http://localhost:8088` if running CKAN locally.

4. Click **"Save"**

#### Option B: Command Line

```bash
ckan -c /etc/ckan/ckan.ini harvester source create \
  name=plateau-mock \
  title="PLATEAU Mock API" \
  url=http://localhost:8088/api/v1/ \
  type=plateau \
  config='{"api_base":"http://mockapi:8088/api/v1/","mode":"rest","list_path":"datasets","detail_path":"datasets/{id}","page_size":10,"owner_org":"plateau-data"}'
```

#### Option C: CKAN API

```bash
curl -X POST http://localhost:5000/api/3/action/harvest_source_create \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "plateau-mock",
    "title": "PLATEAU Mock API",
    "url": "http://localhost:8088/api/v1/",
    "source_type": "plateau",
    "config": "{\"api_base\":\"http://mockapi:8088/api/v1/\",\"mode\":\"rest\",\"list_path\":\"datasets\",\"detail_path\":\"datasets/{id}\",\"page_size\":10,\"owner_org\":\"plateau-data\"}"
  }'
```

### 3. Run Harvest

#### Web UI

1. Go to harvest sources list
2. Click on your source
3. Click **"Reharvest"**

#### Command Line

```bash
# Create a harvest job
ckan -c /etc/ckan/ckan.ini harvester job {source-id}

# Run the harvest
ckan -c /etc/ckan/ckan.ini harvester run

# Or combine both
ckan -c /etc/ckan/ckan.ini harvester job-all  # Create jobs for all sources
ckan -c /etc/ckan/ckan.ini harvester run
```

### 4. Verify Results

Check the harvested datasets:

```bash
# List packages
ckan -c /etc/ckan/ckan.ini search-index rebuild  # Rebuild search if needed
```

Or visit: `http://your-ckan/dataset`

## ⚙️ Configuration

### Source Config JSON Schema

```json
{
  "api_base": "https://api.example.com/v1/",
  "api_key": "optional-api-key",
  "mode": "rest",  // or "graphql"

  // REST mode settings
  "list_path": "datasets",
  "detail_path": "datasets/{id}",

  // GraphQL mode settings
  "graph_path": "graphql",
  "list_query": "query($q:String,$after:String){ datasets(q:$q, after:$after){ nodes{ id title updatedAt } pageInfo{ endCursor hasNextPage }}}",
  "detail_query": "query($id:ID!){ dataset(id:$id){ id title description updatedAt resources{ url name format }}}",

  // Common settings
  "search": "keyword or filter",
  "page_size": 100,
  "owner_org": "organization-name-or-id",
  "extra_headers": {
    "User-Agent": "Custom-Agent"
  }
}
```

### Field Mapping

The `mapping.py` file maps API fields to CKAN package fields. Default mappings:

| API Field | CKAN Field | Notes |
|-----------|------------|-------|
| `id` | `name` | Normalized to URL-safe string |
| `title` | `title` | Dataset title |
| `description` | `notes` | Dataset description |
| `themes`, `keywords` | `tags` | Converted to tag list |
| `city`, `prefecture` | `extras` | Stored as extra fields |
| `year` | `extras` | Model year |
| `modelType` | `extras` | e.g., CityGML, 3D Tiles |
| `resources[]` | `resources` | Files/URLs |
| `updatedAt` | `extras.modified` | Last modified timestamp |

**Customize mapping**: Edit `ckanext/plateau_harvester/mapping.py` → `to_package_dict()` function.

## 📡 API Examples

### REST API Expected Structure

**List endpoint** (`GET /datasets`):
```json
{
  "results": [
    {
      "id": "13100_tokyo_2023",
      "title": "東京都千代田区 3D都市モデル",
      "updatedAt": "2023-12-01T10:00:00Z"
    }
  ]
}
```

**Detail endpoint** (`GET /datasets/{id}`):
```json
{
  "id": "13100_tokyo_2023",
  "title": "東京都千代田区 3D都市モデル",
  "description": "3D都市モデル（CityGML形式）",
  "city": "千代田区",
  "prefecture": "東京都",
  "year": 2023,
  "modelType": "CityGML",
  "themes": ["建築物", "道路"],
  "updatedAt": "2023-12-01T10:00:00Z",
  "resources": [
    {
      "url": "https://example.com/data.gml",
      "name": "建築物モデル",
      "format": "CityGML",
      "size": 1024000
    }
  ]
}
```

### GraphQL API Example

**List query**:
```graphql
query($q: String, $after: String) {
  datasets(query: $q, after: $after, first: 100) {
    nodes {
      id
      title
      updatedAt
    }
    pageInfo {
      endCursor
      hasNextPage
    }
  }
}
```

**Detail query**:
```graphql
query($id: ID!) {
  dataset(id: $id) {
    id
    title
    description
    city
    prefecture
    year
    modelType
    themes
    updatedAt
    resources {
      url
      name
      format
      size
    }
  }
}
```

## 🔧 Customization

### Adjust field mapping

Edit `ckanext/plateau_harvester/mapping.py`:

```python
def to_package_dict(item: Dict[str, Any]) -> Dict[str, Any]:
    # Add your custom mappings here
    title = item.get('myCustomTitle') or item.get('title')

    # Add custom extras
    add_extra('custom_field', item.get('customData'))

    # Filter resources by format
    for res in item.get('resources', []):
        if res.get('format') in ['CityGML', '3DTiles', 'GeoJSON']:
            resources.append({...})
```

### Add authentication

Edit `ckanext/plateau_harvester/http.py`:

```python
def _auth(self, headers: Dict[str, str]) -> Dict[str, str]:
    h = dict(headers)
    if self.api_key:
        # Option 1: Header-based
        h['Authorization'] = f'Bearer {self.api_key}'

        # Option 2: Custom header
        h['X-API-Key'] = self.api_key
    return h
```

### Handle incremental updates

The harvester already handles create vs. update. To filter by date:

```python
# In harvester.py gather_stage()
params = {
    'page': page,
    'modified_since': last_harvest_date  # Get from harvest_job
}
```

## 🐛 Troubleshooting

### Check logs

```bash
# Docker
docker-compose logs -f ckan

# Source install
tail -f /var/log/ckan/ckan.log
```

### Common issues

**1. "No module named 'ckanext.harvest'"**
```bash
pip install ckanext-harvest
```

**2. "Source type 'plateau' not found"**
- Verify plugin is enabled in `ckan.ini`
- Restart CKAN after config changes

**3. "Connection refused to mockapi"**
- Ensure Mock API is running: `docker-compose -f mockapi/docker-compose.yml ps`
- Check network connectivity between CKAN and mockapi containers
- Use correct hostname: `mockapi` (in Docker network) or `localhost` (host network)

**4. Harvest job stuck**
```bash
# Check job status
ckan -c /etc/ckan/ckan.ini harvester jobs

# Clear stuck jobs
ckan -c /etc/ckan/ckan.ini harvester job-abort {job-id}
```

**5. Packages not appearing**
```bash
# Rebuild search index
ckan -c /etc/ckan/ckan.ini search-index rebuild
```

## 📚 Resources

- [CKAN Harvest Documentation](https://github.com/ckan/ckanext-harvest)
- [PLATEAU Project](https://www.mlit.go.jp/plateau/)
- [CKAN API Guide](https://docs.ckan.org/en/latest/api/)

## 📝 License

AGPL-3.0 (same as CKAN)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with mock API
5. Submit a pull request

## 📧 Support

For issues and questions:
- GitHub Issues: [your-repo/issues]
- CKAN Discuss: https://github.com/ckan/ckan/discussions
