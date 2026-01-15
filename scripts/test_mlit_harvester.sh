#!/bin/bash
# Test script for MLIT Harvester

set -e

echo "============================================"
echo "MLIT Harvester Test Script"
echo "============================================"
echo ""

# Step 1: Verify API key is configured
echo "1. Checking if mlit.api_key is configured..."
docker exec ckan grep "mlit.api_key" /srv/app/ckan.ini
echo "✓ API key is configured"
echo ""

# Step 2: Get API token for admin user
echo "2. Getting API token for admin user..."
API_TOKEN=$(docker exec ckan ckan -c /srv/app/ckan.ini user token add admin mlit_test 2>&1 | grep -oP '(?<=API Token created: )[a-zA-Z0-9_\-]+' || docker exec ckan ckan -c /srv/app/ckan.ini user show admin -c /srv/app/ckan.ini 2>&1 | grep -oP '(?<=apikey: )[a-f0-9\-]+')
echo "✓ Got API token"
echo ""

# Step 3: Check if MLIT harvest source exists
echo "3. Checking for existing MLIT harvest sources..."
EXISTING_SOURCE=$(curl -s "http://localhost/api/3/action/package_search?q=type:harvest&rows=100" \
  -H "Authorization: ${API_TOKEN}" | python3 -c "import sys, json; data=json.load(sys.stdin); print([p['name'] for p in data['result']['results'] if 'mlit' in p.get('name','')])") || true
echo "Existing sources: ${EXISTING_SOURCE}"
echo ""

# Step 4: Create a test harvest source (or use existing)
echo "4. Creating/Updating MLIT harvest source..."
SOURCE_NAME="mlit-test-source"
SOURCE_CONFIG='{
  "api_base": "https://api.mlit-data.jp",
  "page_size": 10
}'

# Try to create the source
CREATE_RESULT=$(curl -s -X POST "http://localhost/api/3/action/harvest_source_create" \
  -H "Authorization: ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"${SOURCE_NAME}\",
    \"title\": \"MLIT Test Harvest Source\",
    \"url\": \"https://api.mlit-data.jp\",
    \"source_type\": \"mlit\",
    \"config\": $(echo "${SOURCE_CONFIG}" | jq -c),
    \"owner_org\": \"fukuoka\"
  }" 2>&1)

if echo "${CREATE_RESULT}" | grep -q '"success": true'; then
  echo "✓ Harvest source created successfully"
elif echo "${CREATE_RESULT}" | grep -q "already exists"; then
  echo "✓ Harvest source already exists"
else
  echo "Note: ${CREATE_RESULT}"
fi
echo ""

# Step 5: Show harvest source info
echo "5. Harvest source details:"
curl -s "http://localhost/api/3/action/harvest_source_show?id=${SOURCE_NAME}" \
  -H "Authorization: ${API_TOKEN}" | python3 -m json.tool 2>/dev/null || echo "Source not found yet"
echo ""

# Step 6: Test the harvester Python code directly
echo "6. Testing MLIT harvester code..."
docker exec ckan python3 -c "
from ckanext.mlit_harvester.harvester import MLITHarvester
from ckantoolkit import config

harvester = MLITHarvester()
info = harvester.info()
print(f\"Harvester name: {info['name']}\")
print(f\"Harvester title: {info['title']}\")

# Test config loading
test_config = '{\"api_key\": \"test123\", \"api_base\": \"https://api.mlit-data.jp\"}'
config_result = harvester._load_config(test_config)
print(f\"Config loads successfully: {bool(config_result)}\")
print(f\"API key from config: {'***' + config_result.get('api_key', '')[-6:] if config_result.get('api_key') else 'from ckan.ini'}\")

# Check if ckan.ini api_key is loaded
ckan_api_key = config.get('mlit.api_key', '')
print(f\"API key from ckan.ini: {'***' + ckan_api_key[-6:] if ckan_api_key else 'Not set'}\")
" 2>&1
echo ""

echo "============================================"
echo "Test completed!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. To create a harvest job: docker exec ckan ckan -c /srv/app/ckan.ini harvester job ${SOURCE_NAME}"
echo "2. To run harvest jobs: docker exec ckan ckan -c /srv/app/ckan.ini harvester run"
echo "3. To check job status: curl http://localhost/api/3/action/harvest_source_show_status?id=${SOURCE_NAME} | python3 -m json.tool"
echo ""

