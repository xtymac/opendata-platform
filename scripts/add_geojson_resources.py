#!/usr/bin/env python3
"""
Add GeoJSON resources to Imaginary Cities datasets for map visualization
"""

import json
import requests

CKAN_URL = 'http://localhost'
CKAN_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJScXdsMXhPUW9fbW9NQ1N5Z1NlR2xBMTdCcnNXbTVJU0d3a2ZIS3lKYkgwIiwiaWF0IjoxNzYzNDMzMjUyfQ.ONhcr2o1bQBWW1xXy8Zy0am_j_pQbChsDtFifVewpWQ'

def fetch_reearth_data(endpoint):
    """Fetch data from Re:Earth API"""
    response = requests.get(endpoint)
    response.raise_for_status()
    return response.json().get('results', [])

def create_geojson_from_countries(countries):
    """Convert country data to GeoJSON FeatureCollection"""
    features = []

    for country in countries:
        feature = {
            "type": "Feature",
            "geometry": country.get('boundary', {}),
            "properties": {
                "id": country.get('id'),
                "name": country.get('name'),
                "capital": country.get('capital'),
                "area": country.get('area'),
                "population": country.get('population'),
                "gdp": country.get('gdp')
            }
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    return geojson

def upload_resource(package_id, resource_name, content, format, description=''):
    """Upload resource to CKAN dataset"""
    resource_data = {
        'package_id': package_id,
        'name': resource_name,
        'description': description,
        'format': format.upper()
    }

    files = {
        'upload': (f'{resource_name}.{format.lower()}',
                  content.encode('utf-8') if isinstance(content, str) else content,
                  'application/geo+json' if format.lower() == 'geojson' else 'application/json')
    }

    url = f"{CKAN_URL}/api/3/action/resource_create"
    headers = {'Authorization': CKAN_API_KEY}

    response = requests.post(url, data=resource_data, files=files, headers=headers)
    response.raise_for_status()
    result = response.json()

    if not result.get('success'):
        raise Exception(f"Resource upload error: {result.get('error')}")

    return result.get('result', {})

def main():
    print("=" * 60)
    print("Adding GeoJSON Resources for Map Visualization")
    print("=" * 60)

    # Fetch country data
    print("\n📍 Fetching country data...")
    countries = fetch_reearth_data('https://api.cms.reearth.io/api/p/xgtbhkfgwv/imaginary-cities/country')
    print(f"   Found {len(countries)} countries")

    # Create GeoJSON
    print("\n🗺️  Creating GeoJSON FeatureCollection...")
    geojson = create_geojson_from_countries(countries)
    geojson_content = json.dumps(geojson, indent=2, ensure_ascii=False)

    # Upload to CKAN
    print("\n📤 Uploading GeoJSON resource to CKAN...")
    resource = upload_resource(
        'imaginary-cities-country',
        'countries_boundaries',
        geojson_content,
        'geojson',
        'Country boundaries in GeoJSON format for map visualization'
    )

    print(f"\n✅ GeoJSON resource created!")
    print(f"   Resource ID: {resource['id']}")
    print(f"   Resource URL: {resource['url']}")
    print(f"\n🌍 You can now view the country boundaries on a map!")
    print(f"   Visit: {CKAN_URL}/dataset/imaginary-cities-country")
    print("=" * 60)

if __name__ == '__main__':
    main()
