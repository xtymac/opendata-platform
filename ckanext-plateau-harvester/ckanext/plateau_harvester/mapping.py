"""
Mapping functions to convert PLATEAU API data to CKAN package dictionaries
"""
import re
import hashlib
from typing import Dict, Any, List
from datetime import datetime

from ckan.lib.munge import munge_title_to_name

import logging
log = logging.getLogger(__name__)


def normalize_id(raw: str) -> str:
    """
    Normalize an ID string to be URL-safe

    Args:
        raw: Raw ID string

    Returns:
        Normalized ID suitable for CKAN package name
    """
    raw = re.sub(r'[^0-9A-Za-z_-]+', '-', raw.strip())
    result = raw.strip('-').lower()
    return result or hashlib.sha1(raw.encode('utf-8')).hexdigest()[:16]


def to_package_dict(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert PLATEAU API metadata item to CKAN package dictionary

    This mapping should be adjusted based on the actual API response structure.

    Example input (PLATEAU dataset):
    {
        "id": "13100_tokyo_2023_citygml",
        "title": "東京都千代田区 3D都市モデル",
        "description": "東京都千代田区の3D都市モデル（CityGML形式）",
        "city": "千代田区",
        "prefecture": "東京都",
        "year": 2023,
        "modelType": "CityGML",
        "themes": ["建築物", "道路", "都市計画"],
        "updatedAt": "2023-12-01T10:00:00Z",
        "resources": [
            {
                "url": "https://example.com/data/13100_bldg.gml",
                "name": "建築物モデル",
                "format": "CityGML",
                "size": 1024000,
                "mimetype": "application/xml"
            },
            {
                "url": "https://example.com/data/13100_road.gml",
                "name": "道路モデル",
                "format": "CityGML"
            }
        ]
    }

    Args:
        item: Dictionary from PLATEAU API

    Returns:
        CKAN package dictionary ready for package_create/package_update
    """

    # Extract title
    title = item.get('title') or item.get('name') or 'PLATEAU Dataset'

    # Generate package name
    name_source = item.get('slug') or item.get('id') or title
    name = munge_title_to_name(normalize_id(name_source))

    # Extract description
    notes = item.get('description') or item.get('abstract') or item.get('notes') or ''

    # Extract tags
    tags: List[Dict[str, str]] = []
    tag_sources = item.get('themes') or item.get('keywords') or item.get('tags') or []

    for t in tag_sources:
        if not t:
            continue
        tag_name = munge_title_to_name(str(t))[:100]
        if tag_name:
            tags.append({'name': tag_name})

    # Build extras
    extras = []

    def add_extra(key: str, value: Any):
        """Helper to add extra field"""
        if value is None:
            return
        extras.append({'key': key, 'value': str(value)})

    # Standard PLATEAU metadata
    add_extra('source', item.get('source') or 'PLATEAU')
    add_extra('city', item.get('city') or item.get('municipality'))
    add_extra('prefecture', item.get('prefecture'))
    add_extra('year', item.get('year'))
    add_extra('model_type', item.get('modelType') or item.get('format'))
    add_extra('plateau_id', item.get('id'))
    add_extra('plateau_spec_version', item.get('specVersion'))

    # Timestamps
    modified = item.get('modified') or item.get('updatedAt') or item.get('lastModified')
    if modified:
        add_extra('modified', modified)

    created = item.get('created') or item.get('createdAt')
    if created:
        add_extra('created', created)

    # Spatial extent (if available)
    if item.get('bbox'):
        add_extra('spatial', str(item['bbox']))

    # License
    if item.get('license'):
        add_extra('license_id', item['license'])

    # Extract resources
    resources = []
    for res in (item.get('resources') or []):
        url = res.get('url') or res.get('downloadURL') or res.get('accessURL')
        if not url:
            continue

        r = {
            'url': url,
            'name': res.get('name') or res.get('title') or 'download',
            'description': res.get('description') or '',
        }

        # Format
        format_str = res.get('format') or res.get('mediaType') or ''
        if format_str:
            r['format'] = format_str.upper()[:50]

        # Size
        if res.get('size'):
            r['size'] = res['size']

        # Mimetype
        if res.get('mimetype') or res.get('mediaType'):
            r['mimetype'] = res.get('mimetype') or res.get('mediaType')

        resources.append(r)

    # Build package dictionary
    pkg = {
        'name': name,
        'title': title,
        'notes': notes,
        'owner_org': None,  # Will be set in import stage
        'tags': tags,
        'extras': extras,
        'resources': resources,
    }

    log.debug(f'Mapped item {item.get("id")} to package {name}')

    return pkg
