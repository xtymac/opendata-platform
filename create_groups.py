#!/usr/bin/env python3
"""
Create Groups for CKAN classification
"""
import requests
import json

# CKAN API configuration
CKAN_URL = 'http://localhost:5002'

# Groups to create
GROUPS_TO_CREATE = [
    {
        'name': 'census',
        'title': '国勢調査',
        'description': '人口・世帯数の統計調査に関するデータ',
        'type': 'group'
    },
    {
        'name': 'economic-census',
        'title': '経済センサス',
        'description': '事業所・企業統計調査に関するデータ',
        'type': 'group'
    },
    {
        'name': 'crime-statistics',
        'title': '犯罪統計',
        'description': '犯罪発生状況・治安に関するデータ',
        'type': 'group'
    },
    {
        'name': 'population-statistics',
        'title': '人口統計',
        'description': '人口動態・人口推計に関するデータ',
        'type': 'group'
    },
    {
        'name': 'environment-monitoring',
        'title': '環境モニタリング',
        'description': '環境測定・公害監視に関するデータ',
        'type': 'group'
    }
]

def create_group(group_data, api_key):
    """Create a group using CKAN API"""
    url = f'{CKAN_URL}/api/3/action/group_create'
    headers = {
        'Authorization': api_key,
        'Content-Type': 'application/json'
    }

    response = requests.post(url, json=group_data, headers=headers)

    if response.status_code == 200:
        result = response.json()
        if result['success']:
            print(f"✓ Created group: {group_data['title']} ({group_data['name']})")
            return True
        else:
            print(f"✗ Failed to create group {group_data['name']}: {result.get('error', 'Unknown error')}")
            return False
    else:
        print(f"✗ HTTP error {response.status_code} when creating group {group_data['name']}")
        return False

def main():
    print("Creating Groups for CKAN classification...")

    # Try different API keys
    api_keys = [
        '3tktkCjgM_BtX!',  # From .env
        'ckan_admin',       # Username
        '',                 # No key (for public API)
    ]

    success_count = 0

    for api_key in api_keys:
        print(f"\nTrying with API key: {'***' if api_key else 'None'}")

        for group_data in GROUPS_TO_CREATE:
            if create_group(group_data, api_key):
                success_count += 1
                break  # Move to next group if successful

        if success_count > 0:
            break  # Use this API key for remaining groups

    print(f"\nCompleted: {success_count}/{len(GROUPS_TO_CREATE)} groups created")

    if success_count > 0:
        print("\n✓ Groups created successfully!")
        print("Now you can use these group names in the Groups field:")
        for group in GROUPS_TO_CREATE:
            print(f"  - {group['title']} (use: {group['name']})")
    else:
        print("\n✗ No groups could be created. You may need to:")
        print("  1. Login as admin on the web interface")
        print("  2. Create groups manually via the web interface")
        print("  3. Check API permissions")

if __name__ == '__main__':
    main()