# 🚀 Quick Start Guide - PLATEAU Harvester

Get the PLATEAU harvester running in 5 minutes with the Mock API.

## Prerequisites

- Docker and Docker Compose installed
- CKAN 2.10+ with ckanext-harvest installed
- `plateau_harvester` plugin enabled in `ckan.ini`

## Step-by-Step Setup

### 1. Install the Plugin

```bash
# Clone or copy the plugin
cd /path/to/ckanext-plateau-harvester

# Install
pip install -e .

# Or if using Docker, add to your Dockerfile:
# COPY ./ckanext-plateau-harvester /srv/app/src/ckanext-plateau-harvester
# RUN pip install -e /srv/app/src/ckanext-plateau-harvester
```

### 2. Enable in CKAN

Edit `ckan.ini`:
```ini
ckan.plugins = ... harvest plateau_harvester
```

Restart CKAN:
```bash
docker-compose restart ckan
# or
sudo systemctl restart supervisord
```

### 3. Start Mock API

```bash
cd ckanext-plateau-harvester/mockapi
docker-compose up -d
```

Verify it's running:
```bash
curl http://localhost:8088/health
# Expected: {"status":"ok"}

curl http://localhost:8088/api/v1/datasets
# Expected: JSON with 3 datasets
```

### 4. Create Organization (if needed)

```bash
ckan -c /etc/ckan/ckan.ini organization create \
  name=plateau-data \
  title="PLATEAU Data"
```

Or via web UI: `http://your-ckan/organization/new`

### 5. Create Harvest Source

Choose one method:

#### Method A: Web UI

1. Go to: `http://your-ckan/harvest`
2. Click **"Add Harvest Source"**
3. Fill in:
   ```
   URL: http://mockapi:8088/api/v1/
   Title: PLATEAU Mock API
   Source type: PLATEAU / 3D都市モデル
   Organization: plateau-data
   ```
4. In **Configuration** field, paste:
   ```json
   {
     "api_base": "http://mockapi:8088/api/v1/",
     "mode": "rest",
     "list_path": "datasets",
     "detail_path": "datasets/{id}",
     "page_size": 100,
     "owner_org": "plateau-data"
   }
   ```
5. Click **Save**

#### Method B: Command Line

```bash
ckan -c /etc/ckan/ckan.ini harvester source create \
  plateau-mock \
  "http://mockapi:8088/api/v1/" \
  plateau \
  true \
  "" \
  "" \
  '{"api_base":"http://mockapi:8088/api/v1/","mode":"rest","list_path":"datasets","detail_path":"datasets/{id}","page_size":100,"owner_org":"plateau-data"}'
```

### 6. Run Harvest

#### Web UI

1. Go to harvest source page
2. Click **"Reharvest"**
3. Wait for job to complete

#### Command Line

```bash
# Create job and run
ckan -c /etc/ckan/ckan.ini harvester job-all
ckan -c /etc/ckan/ckan.ini harvester run
```

### 7. Verify Results

```bash
# Check harvest status
ckan -c /etc/ckan/ckan.ini harvester jobs

# Search for harvested datasets
ckan -c /etc/ckan/ckan.ini package search ""

# Or visit web UI
# http://your-ckan/dataset
```

You should see 3 datasets:
- `13100-tokyo-chiyoda-2023` - 東京都千代田区
- `27100-osaka-kita-2023` - 大阪府大阪市北区
- `14100-kanagawa-yokohama-2022` - 神奈川県横浜市

## 🎉 Success!

You've successfully:
- ✅ Installed the PLATEAU harvester plugin
- ✅ Started a mock PLATEAU API
- ✅ Created a harvest source
- ✅ Harvested 3 PLATEAU datasets into CKAN

## Next Steps

### Customize Field Mapping

Edit [mapping.py](ckanext/plateau_harvester/mapping.py) to adjust how API fields map to CKAN:

```python
def to_package_dict(item: Dict[str, Any]) -> Dict[str, Any]:
    # Customize mappings here
    title = item.get('customTitle') or item.get('title')
    # ...
```

### Connect to Real API

Update harvest source configuration:

```json
{
  "api_base": "https://real-plateau-api.example.com/v1/",
  "api_key": "your-api-key",
  "mode": "rest",
  "list_path": "datasets",
  "detail_path": "datasets/{id}",
  "page_size": 100,
  "owner_org": "plateau-data"
}
```

### Schedule Automatic Harvests

Set up cron job:

```bash
# Add to crontab
0 2 * * * /usr/lib/ckan/default/bin/ckan -c /etc/ckan/ckan.ini harvester run
```

Or use CKAN's background jobs (if configured).

### Add More Mock Data

Edit Mock API files in `mockapi/data/`:

```bash
# Add to datasets.json
vi mockapi/data/datasets.json

# Create new detail file
vi mockapi/data/dataset_new_city_2024.json

# Restart mock API
cd mockapi && docker-compose restart
```

## 📖 More Resources

- [Full README](README.md) - Complete documentation
- [Configuration Examples](HARVEST_CONFIG_EXAMPLES.md) - REST, GraphQL, auth examples
- [Mock API README](mockapi/README.md) - Mock API details

## 🐛 Troubleshooting

### "Connection refused" error

If CKAN can't reach Mock API:

**Docker network issue**:
```bash
# Find your CKAN network
docker network ls

# Update mockapi/docker-compose.yml to use same network
networks:
  plateau-network:
    external: true
    name: ckan_default  # Replace with your network name
```

**Use correct hostname**:
- From host machine: `http://localhost:8088`
- From Docker container: `http://mockapi:8088`

### Plugin not found

```bash
# Reinstall plugin
pip install -e /path/to/ckanext-plateau-harvester

# Verify it's installed
pip show ckanext-plateau-harvester

# Check ckan.ini has: plateau_harvester in ckan.plugins
grep "ckan.plugins" /etc/ckan/ckan.ini

# Restart CKAN
docker-compose restart ckan
```

### No datasets after harvest

```bash
# Check harvest job status
ckan -c /etc/ckan/ckan.ini harvester jobs

# View job details
ckan -c /etc/ckan/ckan.ini harvester job-show {job-id}

# Check logs
docker-compose logs -f ckan | grep plateau

# Rebuild search index
ckan -c /etc/ckan/ckan.ini search-index rebuild
```

### Mock API returns 404

```bash
# Check Mock API is running
docker-compose -f mockapi/docker-compose.yml ps

# Test endpoints manually
curl http://localhost:8088/health
curl http://localhost:8088/api/v1/datasets

# Check nginx logs
docker-compose -f mockapi/docker-compose.yml logs mockapi
```

## 💡 Tips

- **Test API first**: Always verify Mock API endpoints work before creating harvest source
- **Check logs**: CKAN logs show detailed error messages for harvest failures
- **Small batches**: Use `page_size: 10` for initial testing
- **Organizations**: Ensure `owner_org` exists before harvesting
- **Network**: Keep CKAN and Mock API on same Docker network for easier communication
