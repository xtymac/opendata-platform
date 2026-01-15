#!/bin/bash
# Quick view script for Imaginary Cities data in CKAN

echo "============================================"
echo "Imaginary Cities Data - Quick View"
echo "============================================"
echo ""

echo "📊 Organization Summary:"
curl -s http://localhost/api/3/action/organization_show?id=imaginary-cities | \
  python3 -c "import sys, json; d=json.load(sys.stdin)['result']; print(f'  Name: {d[\"name\"]}'); print(f'  Title: {d[\"title\"]}'); print(f'  Datasets: {d[\"package_count\"]}')"
echo ""

echo "🌍 Countries Dataset:"
curl -s http://localhost/api/3/action/package_show?id=imaginary-cities-country | \
  python3 -c "import sys, json; d=json.load(sys.stdin)['result']; print(f'  Title: {d[\"title\"]}'); print(f'  Resources: {len(d[\"resources\"])}'); [print(f'    - {r[\"format\"]}: {r[\"name\"]}') for r in d['resources']]"
echo "  🗺️  Map View: ENABLED (geo_view)"
echo ""

echo "🏙️  Cities Dataset:"
curl -s http://localhost/api/3/action/package_show?id=imaginary-cities-city | \
  python3 -c "import sys, json; d=json.load(sys.stdin)['result']; print(f'  Title: {d[\"title\"]}'); print(f'  Resources: {len(d[\"resources\"])}'); [print(f'    - {r[\"format\"]}: {r[\"name\"]}') for r in d['resources']]"
echo ""

echo "🖼️  Assets Dataset:"
curl -s http://localhost/api/3/action/package_show?id=imaginary-cities-assets | \
  python3 -c "import sys, json; d=json.load(sys.stdin)['result']; print(f'  Title: {d[\"title\"]}'); print(f'  Resources: {len(d[\"resources\"])}'); [print(f'    - {r[\"format\"]}: {r[\"name\"]}') for r in d['resources']]"
echo ""

echo "============================================"
echo "🌐 Web Access:"
echo "  https://opendata.uixai.org/organization/imaginary-cities"
echo ""
echo "📖 API Documentation:"
echo "  https://opendata.uixai.org/api/3/action/help_show"
echo "============================================"
