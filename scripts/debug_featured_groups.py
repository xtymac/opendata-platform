#!/usr/bin/env python3
import sys
sys.path.insert(0, '/srv/app/src/ckan')

from ckan import model
from ckan.plugins import toolkit as tk
from ckan.common import config

# Initialize config
from ckan.config.middleware import make_app
from ckan.cli import load_config

conf = load_config('/srv/app/ckan.ini')

# Get featured groups
featured_groups_str = config.get('ckan.featured_groups', '')
print(f"ckan.featured_groups config: '{featured_groups_str}'")

featured_group_names = featured_groups_str.split()
print(f"Split into: {featured_group_names}")

# Try to get groups
context = {'model': model, 'session': model.Session}
for name in featured_group_names:
    try:
        group = tk.get_action('group_show')(context, {'id': name})
        print(f"\nGroup '{name}':")
        print(f"  - Title: {group.get('title')}")
        print(f"  - Package count: {group.get('package_count')}")
        print(f"  - State: {group.get('state')}")
    except Exception as e:
        print(f"\nError getting group '{name}': {e}")
