#!/bin/bash

# PLATEAU Harvester - Quick Test Script
# This script tests the Mock API and provides commands to test the harvester

set -e

echo "=========================================="
echo "PLATEAU Harvester - Testing Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Start Mock API
echo -e "${YELLOW}Step 1: Starting Mock API...${NC}"
cd mockapi
docker-compose up -d
cd ..
sleep 2

# 2. Test Mock API
echo ""
echo -e "${YELLOW}Step 2: Testing Mock API endpoints...${NC}"

echo -n "Testing /health endpoint... "
if curl -s http://localhost:8088/health | grep -q "ok"; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ FAILED${NC}"
    exit 1
fi

echo -n "Testing /api/v1/datasets endpoint... "
if curl -s http://localhost:8088/api/v1/datasets | grep -q "13100_tokyo_chiyoda_2023"; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ FAILED${NC}"
    exit 1
fi

echo -n "Testing dataset detail endpoint... "
if curl -s http://localhost:8088/api/v1/datasets/13100_tokyo_chiyoda_2023 | grep -q "東京都千代田区"; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ FAILED${NC}"
    exit 1
fi

# 3. Show sample responses
echo ""
echo -e "${YELLOW}Step 3: Sample API Responses${NC}"
echo ""
echo "Dataset list:"
curl -s http://localhost:8088/api/v1/datasets | python3 -m json.tool | head -20
echo ""

# 4. Next steps
echo ""
echo -e "${GREEN}✓ Mock API is running successfully!${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Create CKAN organization (if not exists):"
echo "   ckan -c /etc/ckan/ckan.ini organization create name=plateau-data title=\"PLATEAU Data\""
echo ""
echo "2. Create harvest source:"
echo '   ckan -c /etc/ckan/ckan.ini harvester source create plateau-mock "http://mockapi:8088/api/v1/" plateau true "" "" '"'"'{"api_base":"http://mockapi:8088/api/v1/","mode":"rest","list_path":"datasets","detail_path":"datasets/{id}","owner_org":"plateau-data"}'"'"
echo ""
echo "3. Run harvest:"
echo "   ckan -c /etc/ckan/ckan.ini harvester run"
echo ""
echo "4. Check results:"
echo "   ckan -c /etc/ckan/ckan.ini package search plateau"
echo ""
echo "=========================================="
echo "Testing complete!"
echo "=========================================="
