# 📑 PLATEAU Harvester - Complete Index

## 🚀 Quick Links

- **[Quick Start Guide](QUICKSTART.md)** ⭐ - Get running in 5 minutes
- **[Full Documentation](README.md)** - Complete user guide
- **[Configuration Examples](HARVEST_CONFIG_EXAMPLES.md)** - REST, GraphQL, auth configs
- **[Project Summary](PROJECT_SUMMARY.md)** - Architecture & features overview

## 📂 Project Structure

### 📦 **Core Plugin** (`ckanext/plateau_harvester/`)

| File | Description | Lines |
|------|-------------|-------|
| **[plugin.py](ckanext/plateau_harvester/plugin.py)** | CKAN plugin registration | ~40 |
| **[harvester.py](ckanext/plateau_harvester/harvester.py)** | Main harvest logic (gather/fetch/import) | ~400 |
| **[mapping.py](ckanext/plateau_harvester/mapping.py)** | API → CKAN field mapping | ~200 |
| **[http.py](ckanext/plateau_harvester/http.py)** | HTTP/GraphQL client | ~100 |
| **[schemas/sample_source_config.json](ckanext/plateau_harvester/schemas/sample_source_config.json)** | Example config | - |

### 🌐 **Mock API** (`mockapi/`)

| File | Description |
|------|-------------|
| **[docker-compose.yml](mockapi/docker-compose.yml)** | Docker container config (port 8088) |
| **[nginx.conf](mockapi/nginx.conf)** | Nginx reverse proxy config |
| **[README.md](mockapi/README.md)** | Mock API documentation |
| **[data/datasets.json](mockapi/data/datasets.json)** | List endpoint data (3 datasets) |
| **[data/dataset_13100_tokyo_chiyoda_2023.json](mockapi/data/dataset_13100_tokyo_chiyoda_2023.json)** | Tokyo dataset detail |
| **[data/dataset_27100_osaka_kita_2023.json](mockapi/data/dataset_27100_osaka_kita_2023.json)** | Osaka dataset detail |
| **[data/dataset_14100_kanagawa_yokohama_2022.json](mockapi/data/dataset_14100_kanagawa_yokohama_2022.json)** | Yokohama dataset detail |

### 📚 **Documentation**

| File | Purpose |
|------|---------|
| **[README.md](README.md)** | Main documentation (installation, usage, customization) |
| **[QUICKSTART.md](QUICKSTART.md)** | 5-minute setup guide with step-by-step instructions |
| **[HARVEST_CONFIG_EXAMPLES.md](HARVEST_CONFIG_EXAMPLES.md)** | Configuration examples (REST, GraphQL, auth, filters) |
| **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** | Architecture, features, stats, production guide |
| **[INDEX.md](INDEX.md)** | This file - complete project index |

### ⚙️ **Configuration Files**

| File | Purpose |
|------|---------|
| **[setup.py](setup.py)** | Python package setup |
| **[requirements.txt](requirements.txt)** | Python dependencies |
| **[MANIFEST.in](MANIFEST.in)** | Package manifest |
| **[.gitignore](.gitignore)** | Git ignore rules |
| **[LICENSE](LICENSE)** | AGPL-3.0 license |

### 🧪 **Testing**

| File | Purpose |
|------|---------|
| **[TESTING.sh](TESTING.sh)** | Automated test script for Mock API |
| `tests/` | Reserved for unit tests (future) |

## 📊 Dataset Examples (Mock API)

### 1. Tokyo Chiyoda (2023)
- **ID**: `13100_tokyo_chiyoda_2023`
- **Format**: CityGML
- **Resources**: Building, Road, Urban Planning models
- **Size**: ~21 MB

### 2. Osaka Kita (2023)
- **ID**: `27100_osaka_kita_2023`
- **Format**: 3D Tiles
- **Resources**: 3D building/terrain tiles, textures, GeoJSON
- **Size**: ~168 MB

### 3. Yokohama (2022)
- **ID**: `14100_kanagawa_yokohama_2022`
- **Format**: CityGML + GeoJSON + CSV
- **Resources**: Building, road, land use, flood risk data
- **Size**: ~32 MB

## 🎯 Common Tasks

### Installation
```bash
pip install -e .
# Edit ckan.ini: ckan.plugins = ... harvest plateau_harvester
# Restart CKAN
```

### Start Mock API
```bash
cd mockapi && docker-compose up -d
```

### Test Mock API
```bash
./TESTING.sh
```

### Create Harvest Source (REST)
```json
{
  "api_base": "http://mockapi:8088/api/v1/",
  "mode": "rest",
  "list_path": "datasets",
  "detail_path": "datasets/{id}",
  "owner_org": "plateau-data"
}
```

### Create Harvest Source (GraphQL)
```json
{
  "api_base": "https://graphql.example.com/",
  "mode": "graphql",
  "graph_path": "graphql",
  "list_query": "query($after:String){...}",
  "detail_query": "query($id:ID!){...}",
  "owner_org": "plateau-data"
}
```

### Run Harvest
```bash
ckan -c /etc/ckan/ckan.ini harvester run
```

## 🔧 Customization Points

### Field Mapping
**File**: `ckanext/plateau_harvester/mapping.py`
**Function**: `to_package_dict()`

Add custom mappings:
```python
add_extra('custom_field', item.get('customData'))
```

### Authentication
**File**: `ckanext/plateau_harvester/http.py`
**Method**: `_auth()`

Change auth method:
```python
h['Authorization'] = f'Bearer {self.api_key}'
```

### Resource Filtering
**File**: `ckanext/plateau_harvester/mapping.py`

Filter by format:
```python
if res.get('format') in ['CityGML', 'GeoJSON']:
    resources.append(r)
```

## 📈 Feature Comparison

| Feature | REST Mode | GraphQL Mode |
|---------|-----------|--------------|
| List datasets | ✅ Page-based | ✅ Cursor-based |
| Get detail | ✅ Path template | ✅ Query with variables |
| Pagination | ✅ `page`, `page_size` | ✅ `after`, `hasNextPage` |
| Search/Filter | ✅ Query params | ✅ Query variables |
| Authentication | ✅ API key header | ✅ API key header |
| Custom headers | ✅ Supported | ✅ Supported |

## 🛠️ Technology Stack

- **CKAN**: 2.10/2.11
- **Python**: 3.9+
- **Dependencies**:
  - `ckanext-harvest` >= 1.6.0
  - `requests` >= 2.31.0
- **Mock API**:
  - Nginx (Alpine)
  - Docker Compose

## 📦 Files Breakdown

**Total files**: 23

- Python code: 5 files (~1000 lines)
- JSON data: 4 files
- Documentation: 7 files (~2500 lines)
- Configuration: 7 files

## 🚦 Getting Started Paths

### Path 1: Quick Demo (5 minutes)
1. Read [QUICKSTART.md](QUICKSTART.md)
2. Start Mock API
3. Run test script: `./TESTING.sh`
4. Create harvest source
5. Run harvest

### Path 2: Production Setup (30 minutes)
1. Read [README.md](README.md)
2. Install plugin
3. Configure real API (see [HARVEST_CONFIG_EXAMPLES.md](HARVEST_CONFIG_EXAMPLES.md))
4. Customize mappings if needed
5. Schedule cron job

### Path 3: Development (1+ hours)
1. Read [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
2. Understand architecture
3. Review code in `ckanext/plateau_harvester/`
4. Modify mappings/authentication
5. Add tests
6. Contribute back

## 📞 Support & Resources

- **Documentation**: This repository
- **PLATEAU Project**: https://www.mlit.go.jp/plateau/
- **CKAN Harvest**: https://github.com/ckan/ckanext-harvest
- **CKAN API**: https://docs.ckan.org/en/latest/api/
- **Issues**: GitHub Issues (configure your repo)

## ✅ Pre-flight Checklist

Before first run:
- [ ] CKAN 2.10+ installed
- [ ] `ckanext-harvest` installed
- [ ] Plugin installed: `pip install -e .`
- [ ] Plugin enabled in `ckan.ini`
- [ ] CKAN restarted
- [ ] Organization created
- [ ] Mock API tested
- [ ] Harvest source created
- [ ] Ready to harvest!

---

**Quick Start**: Jump to [QUICKSTART.md](QUICKSTART.md) to get running now! 🚀
