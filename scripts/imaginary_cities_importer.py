#!/usr/bin/env python3
"""
Imaginary Cities Data Importer for CKAN
Imports Country, City, and Assets data from Re:Earth API into CKAN
"""

import json
import requests
import csv
import io
import sys
from typing import Dict, List, Any
from datetime import datetime

# API Endpoints
REEARTH_APIS = {
    'country': 'https://api.cms.reearth.io/api/p/xgtbhkfgwv/imaginary-cities/country',
    'city': 'https://api.cms.reearth.io/api/p/xgtbhkfgwv/imaginary-cities/city',
    'assets': 'https://api.cms.reearth.io/api/p/xgtbhkfgwv/imaginary-cities/assets'
}

# CKAN Configuration
CKAN_URL = 'http://localhost'
CKAN_API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJScXdsMXhPUW9fbW9NQ1N5Z1NlR2xBMTdCcnNXbTVJU0d3a2ZIS3lKYkgwIiwiaWF0IjoxNzYzNDMzMjUyfQ.ONhcr2o1bQBWW1xXy8Zy0am_j_pQbChsDtFifVewpWQ'

class ImaginaryCitiesImporter:
    def __init__(self, ckan_url: str, api_key: str):
        self.ckan_url = ckan_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Authorization': api_key,
            'Content-Type': 'application/json'
        }

    def call_ckan_api(self, action: str, data: Dict = None, method: str = 'POST') -> Dict:
        """Call CKAN API endpoint"""
        url = f"{self.ckan_url}/api/3/action/{action}"

        try:
            if method == 'POST':
                response = requests.post(url, json=data, headers=self.headers)
            else:
                response = requests.get(url, params=data, headers=self.headers)

            response.raise_for_status()
            result = response.json()

            if not result.get('success'):
                raise Exception(f"CKAN API error: {result.get('error', 'Unknown error')}")

            return result.get('result', {})
        except requests.exceptions.RequestException as e:
            print(f"Error calling CKAN API ({action}): {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            raise

    def fetch_reearth_data(self, endpoint: str) -> List[Dict]:
        """Fetch data from Re:Earth API"""
        try:
            response = requests.get(endpoint)
            response.raise_for_status()
            data = response.json()
            return data.get('results', [])
        except Exception as e:
            print(f"Error fetching data from {endpoint}: {e}")
            raise

    def create_or_get_organization(self, org_name: str) -> Dict:
        """Create or get organization"""
        try:
            # Try to get existing organization
            return self.call_ckan_api('organization_show', {'id': org_name}, method='GET')
        except:
            # Create new organization
            print(f"Creating organization: {org_name}")
            org_data = {
                'name': org_name,
                'title': 'Imaginary Cities',
                'description': 'Virtual cities and countries data from Re:Earth CMS',
                'image_url': ''
            }
            return self.call_ckan_api('organization_create', org_data)

    def create_or_update_dataset(self, dataset_id: str, dataset_info: Dict) -> Dict:
        """Create or update CKAN dataset"""
        try:
            # Try to get existing dataset
            existing = self.call_ckan_api('package_show', {'id': dataset_id}, method='GET')
            print(f"Updating existing dataset: {dataset_id}")
            dataset_info['id'] = existing['id']
            return self.call_ckan_api('package_update', dataset_info)
        except:
            # Create new dataset
            print(f"Creating new dataset: {dataset_id}")
            dataset_info['name'] = dataset_id
            return self.call_ckan_api('package_create', dataset_info)

    def convert_to_csv(self, data: List[Dict]) -> str:
        """Convert JSON data to CSV format"""
        if not data:
            return ""

        # Flatten nested structures
        flattened_data = []
        for item in data:
            flat_item = {}
            for key, value in item.items():
                if isinstance(value, dict):
                    # Convert dict to JSON string
                    flat_item[key] = json.dumps(value)
                elif isinstance(value, list):
                    flat_item[key] = json.dumps(value)
                else:
                    flat_item[key] = value
            flattened_data.append(flat_item)

        # Create CSV
        output = io.StringIO()
        if flattened_data:
            writer = csv.DictWriter(output, fieldnames=flattened_data[0].keys())
            writer.writeheader()
            writer.writerows(flattened_data)

        return output.getvalue()

    def upload_resource(self, package_id: str, resource_name: str,
                       content: str, format: str, description: str = '') -> Dict:
        """Upload resource to CKAN dataset"""
        resource_data = {
            'package_id': package_id,
            'name': resource_name,
            'description': description,
            'format': format.upper()
        }

        # Create multipart form data
        files = {
            'upload': (f'{resource_name}.{format.lower()}',
                      content.encode('utf-8') if isinstance(content, str) else content,
                      f'text/{format.lower()}' if format == 'csv' else 'application/json')
        }

        url = f"{self.ckan_url}/api/3/action/resource_create"

        try:
            # Don't use Content-Type header for multipart
            headers = {'Authorization': self.api_key}
            response = requests.post(url, data=resource_data, files=files, headers=headers)
            response.raise_for_status()
            result = response.json()

            if not result.get('success'):
                raise Exception(f"Resource upload error: {result.get('error')}")

            return result.get('result', {})
        except Exception as e:
            print(f"Error uploading resource: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            raise

    def import_country_data(self) -> None:
        """Import country data"""
        print("\n=== Importing Country Data ===")

        # Fetch data
        countries = self.fetch_reearth_data(REEARTH_APIS['country'])
        print(f"Fetched {len(countries)} countries")

        # Create dataset
        dataset_info = {
            'title': 'Imaginary Cities - Countries',
            'notes': 'Virtual countries with geographic boundaries and economic data',
            'owner_org': 'imaginary-cities',
            'tags': [
                {'name': 'imaginary'},
                {'name': 'geography'},
                {'name': 'geospatial'},
                {'name': 'countries'}
            ],
            'license_id': 'cc-by'
        }

        dataset = self.create_or_update_dataset('imaginary-cities-country', dataset_info)

        # Upload JSON resource
        json_content = json.dumps(countries, indent=2, ensure_ascii=False)
        self.upload_resource(
            dataset['id'],
            'countries_data',
            json_content,
            'json',
            'Complete country data in JSON format with GeoJSON boundaries'
        )
        print("✓ Uploaded JSON resource")

        # Upload CSV resource
        csv_content = self.convert_to_csv(countries)
        self.upload_resource(
            dataset['id'],
            'countries_data',
            csv_content,
            'csv',
            'Country data in CSV format (boundaries as JSON strings)'
        )
        print("✓ Uploaded CSV resource")

        print(f"✓ Country dataset created: {dataset['name']}")

    def import_city_data(self) -> None:
        """Import city data"""
        print("\n=== Importing City Data ===")

        # Fetch data
        cities = self.fetch_reearth_data(REEARTH_APIS['city'])
        print(f"Fetched {len(cities)} cities")

        # Create dataset
        dataset_info = {
            'title': 'Imaginary Cities - Cities',
            'notes': 'Famous fictional cities from literature, movies, and games including Atlantis, Gotham, Wakanda, etc.',
            'owner_org': 'imaginary-cities',
            'tags': [
                {'name': 'imaginary'},
                {'name': 'cities'},
                {'name': 'fictional'},
                {'name': 'urban'}
            ],
            'license_id': 'cc-by'
        }

        dataset = self.create_or_update_dataset('imaginary-cities-city', dataset_info)

        # Upload JSON resource
        json_content = json.dumps(cities, indent=2, ensure_ascii=False)
        self.upload_resource(
            dataset['id'],
            'cities_data',
            json_content,
            'json',
            'Complete city data with descriptions and statistics'
        )
        print("✓ Uploaded JSON resource")

        # Upload CSV resource
        csv_content = self.convert_to_csv(cities)
        self.upload_resource(
            dataset['id'],
            'cities_data',
            csv_content,
            'csv',
            'City data in CSV format'
        )
        print("✓ Uploaded CSV resource")

        print(f"✓ City dataset created: {dataset['name']}")

    def import_assets_data(self) -> None:
        """Import assets data"""
        print("\n=== Importing Assets Data ===")

        # Fetch data
        assets = self.fetch_reearth_data(REEARTH_APIS['assets'])
        print(f"Fetched {len(assets)} assets")

        # Create dataset
        dataset_info = {
            'title': 'Imaginary Cities - Image Assets',
            'notes': 'Image resources related to imaginary cities',
            'owner_org': 'imaginary-cities',
            'tags': [
                {'name': 'imaginary'},
                {'name': 'images'},
                {'name': 'assets'},
                {'name': 'media'}
            ],
            'license_id': 'cc-by'
        }

        dataset = self.create_or_update_dataset('imaginary-cities-assets', dataset_info)

        # Upload JSON resource
        json_content = json.dumps(assets, indent=2, ensure_ascii=False)
        self.upload_resource(
            dataset['id'],
            'assets_data',
            json_content,
            'json',
            'Image asset URLs and metadata'
        )
        print("✓ Uploaded JSON resource")

        # Upload CSV resource
        csv_content = self.convert_to_csv(assets)
        self.upload_resource(
            dataset['id'],
            'assets_data',
            csv_content,
            'csv',
            'Asset data in CSV format'
        )
        print("✓ Uploaded CSV resource")

        print(f"✓ Assets dataset created: {dataset['name']}")

    def run(self) -> None:
        """Run the complete import process"""
        print("=" * 60)
        print("Imaginary Cities Data Importer")
        print("=" * 60)

        try:
            # Create organization
            print("\n=== Creating/Getting Organization ===")
            org = self.create_or_get_organization('imaginary-cities')
            print(f"✓ Organization ready: {org['name']}")

            # Import all datasets
            self.import_country_data()
            self.import_city_data()
            self.import_assets_data()

            print("\n" + "=" * 60)
            print("✓ Import completed successfully!")
            print("=" * 60)
            print(f"\nView datasets at: {self.ckan_url}/organization/imaginary-cities")

        except Exception as e:
            print(f"\n✗ Import failed: {e}")
            sys.exit(1)


def main():
    importer = ImaginaryCitiesImporter(CKAN_URL, CKAN_API_KEY)
    importer.run()


if __name__ == '__main__':
    main()
