#!/usr/bin/env python3
"""
Remove duplicate resources from CKAN dataset
"""
import requests
import sys

# CKAN API configuration
CKAN_URL = 'http://localhost:5002'
API_KEY = '3tktkCjgM_BtX!'  # Admin API key from .env
DATASET_ID = 'yamaguchi-population-20200531'

# Resource IDs to delete (keep the latest one)
RESOURCES_TO_DELETE = [
    '67075cda-c2b2-4e94-af16-639c26414a29',  # First duplicate
    'e940a1c4-19f1-4910-88d9-2e0ce1458d85'   # Second duplicate
]

def delete_resource(resource_id):
    """Delete a resource using CKAN API"""
    url = f'{CKAN_URL}/api/3/action/resource_delete'
    headers = {
        'Authorization': API_KEY,
        'Content-Type': 'application/json'
    }
    data = {'id': resource_id}

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        result = response.json()
        if result['success']:
            print(f"✓ Successfully deleted resource {resource_id}")
            return True
        else:
            print(f"✗ Failed to delete resource {resource_id}: {result.get('error', 'Unknown error')}")
            return False
    else:
        print(f"✗ HTTP error {response.status_code} when deleting resource {resource_id}")
        return False

def main():
    print(f"Removing duplicate resources from dataset {DATASET_ID}...")

    success_count = 0
    for resource_id in RESOURCES_TO_DELETE:
        if delete_resource(resource_id):
            success_count += 1

    print(f"\nCompleted: {success_count}/{len(RESOURCES_TO_DELETE)} resources deleted")

    if success_count == len(RESOURCES_TO_DELETE):
        print("✓ All duplicate resources removed successfully!")
        return 0
    else:
        print("✗ Some resources could not be deleted")
        return 1

if __name__ == '__main__':
    sys.exit(main())