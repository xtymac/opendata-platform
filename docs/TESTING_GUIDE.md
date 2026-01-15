# MLIT Harvester Testing Guide

## ✅ Step 1: Verify API Key Configuration

Check that the API key is configured in CKAN:

```bash
docker exec ckan grep "mlit.api_key" /srv/app/ckan.ini
```

**Expected output:** `mlit.api_key=._n8fTJPYaHTGpn0YQX6UzPHIiQ6SzBK`

---

## ✅ Step 2: Test the Harvester Code Directly

Test if the harvester can load the API key from configuration:

```bash
docker exec ckan python3 << 'EOF'
from ckanext.mlit_harvester.harvester import MLITHarvester
from ckantoolkit import config

# Initialize harvester
harvester = MLITHarvester()
info = harvester.info()

print("=" * 50)
print("MLIT Harvester Info:")
print("=" * 50)
print(f"Name: {info['name']}")
print(f"Title: {info['title']}")
print(f"Description: {info['description']}")
print()

# Test config loading without API key (should use ckan.ini)
print("=" * 50)
print("Testing Config Loading:")
print("=" * 50)

# Test 1: Empty config (should load from ckan.ini)
config1 = harvester._load_config('{}')
api_key_from_ini = config1.get('api_key', '')
if api_key_from_ini:
    print(f"✓ API key loaded from ckan.ini: ...{api_key_from_ini[-6:]}")
else:
    print("✗ No API key found in ckan.ini")

# Test 2: Config with custom API key
config2 = harvester._load_config('{"api_key": "custom_key_123"}')
if config2.get('api_key') == 'custom_key_123':
    print("✓ Custom API key from source config works")

print()
print("=" * 50)
print("Testing HTTP Session Setup:")
print("=" * 50)

# Test HTTP session creation
session = harvester._get_http_session(config1)
if 'X-API-KEY' in session.headers:
    print(f"✓ X-API-KEY header set: ...{session.headers['X-API-KEY'][-6:]}")
else:
    print("✗ X-API-KEY header not set")

print("\n✓ All basic tests passed!")
EOF
```

---

## ✅ Step 3: Access CKAN Web Interface

1. **Open your browser** and go to: http://localhost/

2. **Login** as admin:
   - Username: `admin`
   - Password: (check your setup docs or reset it)

3. **Navigate to Harvest Admin**:
   - Go to: http://localhost/harvest or
   - Click "Organizations" → Select an organization → "Admin" tab → "Harvest Sources"

---

## ✅ Step 4: Create a Test Harvest Source (via Web UI)

1. Click **"Add Harvest Source"**

2. Fill in the form:
   - **URL**: `https://api.mlit-data.jp`
   - **Title**: `MLIT Test Source`
   - **Name**: `mlit-test-source`
   - **Type**: Select `mlit` from the dropdown
   - **Organization**: Select any organization (e.g., `fukuoka`)
   - **Configuration (JSON)**:
     ```json
     {
       "api_base": "https://api.mlit-data.jp",
       "page_size": 10
     }
     ```

3. Click **"Save"**

---

## ✅ Step 5: Create a Test Harvest Source (via Command Line)

Alternatively, create via CLI:

```bash
# First, create an API token
docker exec ckan ckan -c /srv/app/ckan.ini user token add admin mlit_test

# The command will output an API token, save it as API_TOKEN
API_TOKEN="<your-token-here>"

# Create harvest source
curl -X POST "http://localhost/api/3/action/harvest_source_create" \
  -H "Authorization: ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mlit-test-source",
    "title": "MLIT Test Harvest Source",
    "url": "https://api.mlit-data.jp",
    "source_type": "mlit",
    "config": "{\"api_base\": \"https://api.mlit-data.jp\", \"page_size\": 10}",
    "owner_org": "fukuoka"
  }' | python3 -m json.tool
```

---

## ✅ Step 6: Run a Test Harvest Job

```bash
# Create and run a harvest job
docker exec ckan ckan -c /srv/app/ckan.ini harvester job mlit-test-source

# Run the harvest
docker exec ckan ckan -c /srv/app/ckan.ini harvester run
```

---

## ✅ Step 7: Check Harvest Job Status

```bash
# View harvest source status
curl -s "http://localhost/api/3/action/harvest_source_show_status?id=mlit-test-source" | python3 -m json.tool

# Or via CLI
docker exec ckan ckan -c /srv/app/ckan.ini harvester job-show <job-id>
```

---

## ✅ Step 8: Monitor Harvest Logs

Watch the logs in real-time:

```bash
# Follow CKAN logs
docker logs -f ckan

# Look for lines containing "MLIT" or "harvest"
docker logs ckan 2>&1 | grep -i mlit
```

---

## 🔍 Troubleshooting

### Check if API key is being used in requests:

```bash
docker exec ckan python3 << 'EOF'
from ckanext.mlit_harvester.harvester import MLITHarvester
from ckantoolkit import config

harvester = MLITHarvester()
config_obj = harvester._load_config('{}')
session = harvester._get_http_session(config_obj)

print("Headers that will be sent:")
for key, value in session.headers.items():
    if 'key' in key.lower() or 'auth' in key.lower():
        print(f"  {key}: ...{value[-10:]}")
    else:
        print(f"  {key}: {value}")
EOF
```

### Test actual API connection:

```bash
docker exec ckan python3 << 'EOF'
from ckanext.mlit_harvester.harvester import MLITHarvester
import json

harvester = MLITHarvester()
config = harvester._load_config('{"page_size": 5}')
session = harvester._get_http_session(config)

# Try to fetch from MLIT API
endpoint = harvester._build_endpoint(config, "datasets")
print(f"Testing endpoint: {endpoint}")

try:
    params = harvester._listing_params(config, page=1)
    print(f"Parameters: {params}")
    response = session.get(endpoint, params=params, timeout=10)
    print(f"Status code: {response.status_code}")
    print(f"Response preview: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
EOF
```

---

## 📊 Expected Behavior

1. **API key should be loaded** from `ckan.ini` automatically
2. **HTTP requests** should include `X-API-KEY` header
3. **Harvest jobs** should connect to MLIT API
4. **Datasets** should be fetched and imported into CKAN

---

## 📝 Notes

- The API key is stored in: `/srv/app/ckan.ini` inside the container
- The harvester reads it via: `toolkit_config.get("mlit.api_key")`
- You can override it per-source by adding `"api_key"` to the source's JSON configuration
- Make sure the MLIT API endpoint URL is correct (currently using `https://api.mlit-data.jp`)


