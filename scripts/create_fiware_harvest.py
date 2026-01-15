#!/usr/bin/env python3
"""Create FIWARE harvest source using CKAN API."""

import requests
import json

# CKAN API endpoint
CKAN_URL = "http://localhost"
API_KEY = "your-api-key-here"  # Will use default sysadmin

# Harvest source configuration
source_config = {
    "name": "fiware-orion-test",
    "title": "FIWARE Orion Test (After Bug Fix)",
    "url": "http://orion:1026",
    "source_type": "fiware_orion",
    "active": True,
    "owner_org": "imaginary-cities",
    "frequency": "MANUAL",
    "config": json.dumps({
        "api_version": "v2",
        "entity_types": ["Building", "AirQualityObserved", "WeatherObserved", "PointOfInterest"],
        "entity_limit": 50
    })
}

# Create harvest source
print("Creating FIWARE harvest source...")
print(f"URL: {source_config['url']}")
print(f"Title: {source_config['title']}")
print(f"Config: {source_config['config']}")
print()

# Use internal API call via ckan command
import subprocess
import sys

# Build command
cmd = [
    "docker", "exec", "ckan",
    "python3", "-c",
    f"""
import ckan.model as model
from ckanext.harvest.model import HarvestSource, HarvestJob
import json

# Connect to database
model.Session.close_all()
model.repo.rebuild_db()

# Create source
source = HarvestSource(
    url='{source_config['url']}',
    title='{source_config['title']}',
    type='harvest',
    source_type='{source_config['source_type']}',
    frequency='MANUAL',
    active=True,
    config='{source_config['config']}',
    owner_org='imaginary-cities'
)

source.save()
print(f"Created harvest source: {{source.id}}")
print(f"  URL: {{source.url}}")
print(f"  Title: {{source.title}}")
"""
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print(f"Exit code: {result.returncode}")
except Exception as e:
    print(f"Error: {e}")
