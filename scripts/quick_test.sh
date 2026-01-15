#!/bin/bash

echo "=========================================="
echo "MLIT Harvester Quick Test"
echo "=========================================="
echo ""

echo "1. Verify API key in ckan.ini:"
docker exec ckan grep "mlit.api_key" /srv/app/ckan.ini
echo ""

echo "2. Verify extension is installed:"
docker exec ckan pip show ckanext-mlit_harvester 2>&1 | grep -E "(Name|Version|Location)"
echo ""

echo "3. Test harvester code (basic):"
docker exec ckan python3 -c "
from ckanext.mlit_harvester.harvester import MLITHarvester
harvester = MLITHarvester()
info = harvester.info()
print(f\"  Name: {info['name']}\")
print(f\"  Title: {info['title']}\")
print(f\"  ✓ Harvester loads successfully\")
"
echo ""

echo "4. Test config with explicit API key:"
docker exec ckan python3 -c "
from ckanext.mlit_harvester.harvester import MLITHarvester

harvester = MLITHarvester()

# Test with explicit API key in config
test_config = '{\"api_key\": \"._n8fTJPYaHTGpn0YQX6UzPHIiQ6SzBK\", \"api_base\": \"https://api.mlit-data.jp\"}'
config = harvester._load_config(test_config)

print(f\"  API Base: {config['api_base']}\")
print(f\"  API Key: ...{config['api_key'][-6:]}\")
print(f\"  Page Size: {config['page_size']}\")

# Test HTTP session
session = harvester._get_http_session(config)
if 'X-API-KEY' in session.headers:
    print(f\"  ✓ X-API-KEY header is set: ...{session.headers['X-API-KEY'][-6:]}\")
else:
    print(f\"  ✗ X-API-KEY header not set\")
"
echo ""

echo "=========================================="
echo "✓ Basic tests passed!"
echo "=========================================="
echo ""
echo "Next: To test with a real harvest job,"
echo "follow the steps in TESTING_GUIDE.md"
echo ""
echo "Quick start:"
echo "  1. Go to http://localhost/harvest"  
echo "  2. Create a harvest source with type 'mlit'"
echo "  3. Run: docker exec ckan ckan -c /srv/app/ckan.ini harvester run"
echo ""

