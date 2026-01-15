# PLATEAU Harvester Plugin - Project Summary

## 📦 What's Included

A complete, production-ready CKAN harvester plugin for collecting PLATEAU (3D都市モデル) datasets.

### Core Components

#### 1. **Plugin Code** (`ckanext/plateau_harvester/`)
- `plugin.py` - CKAN plugin registration
- `harvester.py` - Main harvester logic (gather/fetch/import stages)
- `mapping.py` - API-to-CKAN field mapping
- `http.py` - HTTP client for REST/GraphQL APIs
- `schemas/sample_source_config.json` - Example configuration

#### 2. **Mock API** (`mockapi/`)
- Nginx-based REST API serving sample PLATEAU data
- 3 sample datasets (Tokyo, Osaka, Yokohama)
- Runs on port 8088
- Zero-dependency testing

#### 3. **Documentation**
- `README.md` - Complete user guide
- `QUICKSTART.md` - 5-minute setup guide
- `HARVEST_CONFIG_EXAMPLES.md` - Configuration examples
- `mockapi/README.md` - Mock API documentation

#### 4. **Configuration**
- `setup.py` - Python package setup
- `requirements.txt` - Dependencies
- `docker-compose.yml` - Mock API container
- `.gitignore` - Git ignore rules

## 🎯 Features

✅ **Dual API Support**: REST and GraphQL modes
✅ **Three-Stage Harvest**: Gather → Fetch → Import
✅ **Flexible Mapping**: Customizable field transformations
✅ **Pagination**: REST (page-based) and GraphQL (cursor-based)
✅ **Authentication**: API key support with custom headers
✅ **Search/Filter**: Built-in query parameter support
✅ **Incremental Updates**: Create new or update existing packages
✅ **Organization Support**: Assign datasets to CKAN organizations
✅ **Resource Handling**: Multiple file formats (CityGML, 3D Tiles, GeoJSON)

## 📂 File Structure

```
ckanext-plateau-harvester/
├── README.md                          # Main documentation
├── QUICKSTART.md                      # Quick start guide
├── HARVEST_CONFIG_EXAMPLES.md         # Config examples
├── PROJECT_SUMMARY.md                 # This file
├── setup.py                           # Package setup
├── requirements.txt                   # Dependencies
├── MANIFEST.in                        # Package manifest
├── .gitignore                         # Git ignore
│
├── ckanext/
│   ├── __init__.py                    # Namespace package
│   └── plateau_harvester/
│       ├── __init__.py                # Plugin init
│       ├── plugin.py                  # CKAN plugin entry point
│       ├── harvester.py               # Core harvester (400+ lines)
│       ├── mapping.py                 # Field mapping logic
│       ├── http.py                    # HTTP/GraphQL client
│       └── schemas/
│           └── sample_source_config.json
│
├── mockapi/
│   ├── README.md                      # Mock API docs
│   ├── docker-compose.yml             # Container config
│   ├── nginx.conf                     # Nginx config
│   └── data/
│       ├── datasets.json              # List endpoint
│       ├── dataset_13100_tokyo_chiyoda_2023.json
│       ├── dataset_27100_osaka_kita_2023.json
│       └── dataset_14100_kanagawa_yokohama_2022.json
│
└── tests/                             # (Reserved for future tests)
```

## 🚀 Installation Summary

### 1. Install Plugin
```bash
pip install -e /path/to/ckanext-plateau-harvester
```

### 2. Enable in CKAN
```ini
# ckan.ini
ckan.plugins = ... harvest plateau_harvester
```

### 3. Start Mock API
```bash
cd mockapi && docker-compose up -d
```

### 4. Create Harvest Source
```bash
ckan harvester source create \
  plateau-mock \
  "http://mockapi:8088/api/v1/" \
  plateau \
  true \
  "" \
  "" \
  '{"api_base":"http://mockapi:8088/api/v1/","mode":"rest","list_path":"datasets","detail_path":"datasets/{id}","owner_org":"plateau-data"}'
```

### 5. Run Harvest
```bash
ckan harvester run
```

## 🔧 Configuration Options

### Basic REST Config
```json
{
  "api_base": "http://api.example.com/v1/",
  "mode": "rest",
  "list_path": "datasets",
  "detail_path": "datasets/{id}",
  "page_size": 100,
  "owner_org": "plateau-data"
}
```

### GraphQL Config
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

### With Authentication
```json
{
  "api_base": "https://api.example.com/v1/",
  "api_key": "your-key",
  "mode": "rest",
  "extra_headers": {"User-Agent": "Custom"}
}
```

## 📊 Sample Data

### Mock API provides 3 datasets:

1. **Tokyo Chiyoda (2023)** - `13100_tokyo_chiyoda_2023`
   - Format: CityGML
   - Resources: Building, Road, Urban Planning, Metadata
   - Size: ~21 MB total

2. **Osaka Kita (2023)** - `27100_osaka_kita_2023`
   - Format: 3D Tiles
   - Resources: Building 3D Tiles, Terrain, Textures, GeoJSON footprint
   - Size: ~168 MB total

3. **Yokohama (2022)** - `14100_kanagawa_yokohama_2022`
   - Format: CityGML + GeoJSON + CSV
   - Resources: Building, Road, Land Use, Flood Risk, Attributes
   - Size: ~32 MB total

## 🔄 Harvest Process Flow

```
1. GATHER STAGE
   ├── Connect to API (REST or GraphQL)
   ├── Fetch list of dataset IDs (paginated)
   ├── Create HarvestObject for each ID
   └── Return list of HarvestObject IDs

2. FETCH STAGE (for each HarvestObject)
   ├── Retrieve full metadata using ID
   ├── Store JSON in HarvestObject.content
   └── Save to database

3. IMPORT STAGE (for each HarvestObject)
   ├── Parse JSON content
   ├── Map fields to CKAN package_dict
   ├── Check if package exists
   ├── Create new or update existing package
   └── Save to CKAN
```

## 🗺️ Field Mapping

| PLATEAU Field | CKAN Field | Type | Notes |
|---------------|------------|------|-------|
| `id` | `name` | string | URL-safe normalized |
| `title` | `title` | string | Dataset title |
| `description` | `notes` | text | Full description |
| `themes`, `keywords` | `tags` | array | Tag list |
| `city` | `extras.city` | string | Municipality |
| `prefecture` | `extras.prefecture` | string | Prefecture |
| `year` | `extras.year` | integer | Model year |
| `modelType` | `extras.model_type` | string | CityGML, 3D Tiles, etc. |
| `updatedAt` | `extras.modified` | datetime | Last modified |
| `resources[]` | `resources` | array | Downloadable files |
| `bbox` | `extras.spatial` | string | Bounding box |
| `license` | `extras.license_id` | string | License |

## 🧪 Testing

### Manual Test with Mock API

```bash
# 1. Start Mock API
cd mockapi && docker-compose up -d

# 2. Test endpoints
curl http://localhost:8088/api/v1/datasets
curl http://localhost:8088/api/v1/datasets/13100_tokyo_chiyoda_2023

# 3. Run harvest
ckan harvester source create plateau-test ...
ckan harvester run

# 4. Verify results
ckan package search plateau
```

### Unit Tests (Future)

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/

# With coverage
pytest --cov=ckanext.plateau_harvester tests/
```

## 🌐 Network Configuration

### CKAN and Mock API on Same Docker Network

```yaml
# mockapi/docker-compose.yml
networks:
  plateau-network:
    external: true
    name: ckan_default  # Your CKAN network
```

Config: Use `http://mockapi:8088`

### CKAN on Host, Mock API in Docker

Config: Use `http://localhost:8088`

### Both on Host

Config: Use `http://localhost:8088`

## 📈 Scaling Considerations

- **Large datasets**: Increase `page_size` carefully (balance API limits vs memory)
- **Rate limiting**: Add delays in HTTP client if needed
- **Concurrent harvests**: Use CKAN's background job queue
- **Resource filtering**: Filter by format in `mapping.py` to reduce dataset size

## 🔒 Security Notes

- API keys stored in harvest source config (encrypted in CKAN)
- Use HTTPS for production APIs
- Validate SSL certificates in production
- Consider IP whitelisting for harvest sources
- Review harvested content before making public

## 🐛 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Connection refused | Check Docker network, use correct hostname |
| Plugin not found | Reinstall, check `ckan.ini`, restart CKAN |
| No datasets created | Check logs, verify org exists, rebuild search index |
| Mock API 404 | Verify file names match dataset IDs |
| Harvest job stuck | Abort job, check for errors, retry |

## 📝 Customization Guide

### Add Custom Field Mapping

Edit `mapping.py`:
```python
def to_package_dict(item):
    # Add custom field
    add_extra('custom_field', item.get('customData'))
```

### Change Authentication Method

Edit `http.py`:
```python
def _auth(self, headers):
    h['Authorization'] = f'Bearer {self.api_key}'
```

### Filter Resources

Edit `mapping.py`:
```python
# Only include CityGML and GeoJSON
if res.get('format') in ['CityGML', 'GeoJSON']:
    resources.append(r)
```

## 🚀 Production Deployment

1. **Install on CKAN server**:
   ```bash
   pip install -e /srv/app/src/ckanext-plateau-harvester
   ```

2. **Configure harvest source** with real API

3. **Set up cron job**:
   ```cron
   0 2 * * * /usr/bin/ckan -c /etc/ckan/ckan.ini harvester run
   ```

4. **Monitor logs**:
   ```bash
   tail -f /var/log/ckan/ckan.log | grep plateau
   ```

5. **Set up alerts** for failed harvest jobs

## 📚 Resources

- [PLATEAU Official Site](https://www.mlit.go.jp/plateau/)
- [CKAN Harvest Docs](https://github.com/ckan/ckanext-harvest)
- [CKAN API Docs](https://docs.ckan.org/en/latest/api/)
- [CityGML Standard](https://www.ogc.org/standards/citygml)
- [3D Tiles Spec](https://github.com/CesiumGS/3d-tiles)

## 📊 Stats

- **Total Files**: 19
- **Python Code**: ~1000 lines
- **Documentation**: ~1500 lines
- **Sample Data**: 3 datasets, 12 resources
- **Supported Formats**: CityGML, 3D Tiles, GeoJSON, XML, CSV, ZIP
- **API Modes**: REST + GraphQL
- **Test Coverage**: Mock API ready, unit tests pending

## ✅ Checklist for Going Live

- [ ] Plugin installed and enabled
- [ ] Real API configuration tested
- [ ] Field mapping adjusted for your data
- [ ] Organization created in CKAN
- [ ] Authentication configured (if needed)
- [ ] Initial harvest successful
- [ ] Search index rebuilt
- [ ] Cron job scheduled
- [ ] Monitoring set up
- [ ] Documentation updated

## 🤝 Contributing

To extend this plugin:

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test with Mock API
5. Update documentation
6. Submit pull request

## 📧 Support

- GitHub Issues: [your-repo/issues]
- CKAN Discuss: https://github.com/ckan/ckan/discussions
- Email: plateau@example.com

---

**Built with ❤️ for the PLATEAU community**
