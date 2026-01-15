#!/usr/bin/env python3
"""Test FIWARE harvester directly without job queue."""

import sys
sys.path.insert(0, '/srv/app/src/ckanext-fiware-orion')

from ckanext.fiware_orion.harvester import FiwareOrionHarvester
import json

# Create harvester instance
harvester = FiwareOrionHarvester()

# Test configuration
config = {
    "orion_url": "http://orion:1026",
    "api_version": "v2",
    "entity_types": ["Building", "AirQualityObserved", "WeatherObserved", "PointOfInterest"],
    "entity_limit": 50
}

print("=" * 60)
print("Testing FIWARE Orion Harvester")
print("=" * 60)
print(f"Orion URL: {config['orion_url']}")
print(f"API Version: {config['api_version']}")
print(f"Entity Types: {', '.join(config['entity_types'])}")
print()

# Load config
try:
    loaded_config = harvester._load_config(json.dumps(config), config['orion_url'])
    print("✓ Configuration loaded successfully")
    print(f"  Final Orion URL: {loaded_config['orion_url']}")
except Exception as e:
    print(f"✗ Failed to load config: {e}")
    sys.exit(1)

# Get HTTP session
try:
    session = harvester._get_http_session(loaded_config)
    print("✓ HTTP session created")
    print(f"  Headers: {dict(session.headers)}")
except Exception as e:
    print(f"✗ Failed to create session: {e}")
    sys.exit(1)

# Fetch entities
print()
print("Fetching entities from Orion...")
try:
    entities = harvester._fetch_entities(session, loaded_config, offset=0, limit=50)
    print(f"✓ Successfully fetched {len(entities)} entities")
    print()
    for i, entity in enumerate(entities, 1):
        entity_id = entity.get('id', 'unknown')
        entity_type = entity.get('type', 'unknown')
        print(f"  {i}. [{entity_type}] {entity_id}")
except Exception as e:
    print(f"✗ Failed to fetch entities: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
print("✓ HARVESTER TEST SUCCESSFUL!")
print("=" * 60)
print()
print(f"The bug fix works! We can now harvest {len(entities)} entities from Orion.")
