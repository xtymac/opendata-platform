"""Data transformers for CMS-CKAN Sync Service"""

import csv
import io
import json
from typing import Any, Dict, List, Optional

from .logger import get_logger

log = get_logger("cms_ckan_sync.transformers")


def flatten_value(value: Any) -> str:
    """
    Flatten a value for CSV output.

    Complex types (dict, list) are JSON-serialized.

    Args:
        value: Value to flatten

    Returns:
        String representation of the value
    """
    if value is None:
        return ""
    elif isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    elif isinstance(value, bool):
        return str(value).lower()
    else:
        return str(value)


def apply_field_mappings(
    data: Dict[str, Any],
    field_mappings: Dict[str, str],
    exclude_fields: List[str]
) -> Dict[str, Any]:
    """
    Apply field mappings and exclusions to data.

    Args:
        data: Original data dictionary
        field_mappings: Mapping of original field names to new names
        exclude_fields: Fields to exclude

    Returns:
        Transformed data dictionary
    """
    result = {}

    for key, value in data.items():
        # Skip excluded fields
        if key in exclude_fields:
            continue

        # Apply mapping or use original key
        new_key = field_mappings.get(key, key)
        result[new_key] = value

    return result


def json_to_csv(
    data: List[Dict[str, Any]],
    field_mappings: Optional[Dict[str, str]] = None,
    exclude_fields: Optional[List[str]] = None
) -> str:
    """
    Transform JSON data to CSV format.

    Args:
        data: List of dictionaries to transform
        field_mappings: Optional field name mappings
        exclude_fields: Optional fields to exclude

    Returns:
        CSV content as string
    """
    if not data:
        log.warning("No data to transform to CSV")
        return ""

    field_mappings = field_mappings or {}
    exclude_fields = exclude_fields or []

    # Process data
    processed_data = []
    ordered_keys = []  # Preserve field order from first record
    seen_keys = set()

    for item in data:
        # Apply mappings and exclusions
        processed_item = apply_field_mappings(item, field_mappings, exclude_fields)

        # Flatten nested values
        flattened_item = {k: flatten_value(v) for k, v in processed_item.items()}
        processed_data.append(flattened_item)

        # Preserve key order from the data (add new keys in the order they appear)
        for key in flattened_item.keys():
            if key not in seen_keys:
                ordered_keys.append(key)
                seen_keys.add(key)

    # Use the original field order (not alphabetically sorted)
    sorted_keys = ordered_keys

    # Write CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=sorted_keys, extrasaction='ignore')
    writer.writeheader()

    for item in processed_data:
        # Ensure all keys exist
        row = {k: item.get(k, '') for k in sorted_keys}
        writer.writerow(row)

    csv_content = output.getvalue()
    log.info(f"Transformed {len(processed_data)} records to CSV ({len(sorted_keys)} columns)")

    return csv_content


def extract_geometry(
    item: Dict[str, Any],
    geometry_field: str
) -> Optional[Dict[str, Any]]:
    """
    Extract geometry from an item.

    Handles various geometry formats:
    - Direct GeoJSON geometry object
    - Point with lat/lng or latitude/longitude
    - Nested location object

    Args:
        item: Data item
        geometry_field: Field name containing geometry

    Returns:
        GeoJSON geometry object or None
    """
    geometry_data = item.get(geometry_field)

    if geometry_data is None:
        return None

    # If it's already a GeoJSON geometry
    if isinstance(geometry_data, dict):
        geo_type = geometry_data.get('type')
        if geo_type in ['Point', 'LineString', 'Polygon', 'MultiPoint',
                        'MultiLineString', 'MultiPolygon', 'GeometryCollection']:
            return geometry_data

        # Check for lat/lng format
        lat = geometry_data.get('lat') or geometry_data.get('latitude')
        lng = geometry_data.get('lng') or geometry_data.get('lon') or geometry_data.get('longitude')

        if lat is not None and lng is not None:
            return {
                'type': 'Point',
                'coordinates': [float(lng), float(lat)]
            }

    # Check for separate lat/lng fields in item
    lat = item.get('lat') or item.get('latitude')
    lng = item.get('lng') or item.get('lon') or item.get('longitude')

    if lat is not None and lng is not None:
        return {
            'type': 'Point',
            'coordinates': [float(lng), float(lat)]
        }

    return None


def json_to_geojson(
    data: List[Dict[str, Any]],
    geometry_field: str,
    properties_exclude: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Transform JSON data to GeoJSON FeatureCollection.

    Args:
        data: List of dictionaries to transform
        geometry_field: Field name containing geometry data
        properties_exclude: Fields to exclude from properties

    Returns:
        GeoJSON FeatureCollection or None if no valid geometries
    """
    if not data:
        log.warning("No data to transform to GeoJSON")
        return None

    properties_exclude = properties_exclude or []
    properties_exclude.append(geometry_field)

    features = []
    skipped = 0

    for item in data:
        geometry = extract_geometry(item, geometry_field)

        if geometry is None:
            skipped += 1
            continue

        # Build properties (exclude geometry field and other exclusions)
        properties = {}
        for key, value in item.items():
            if key not in properties_exclude:
                # Simplify complex values for properties
                if isinstance(value, (dict, list)):
                    properties[key] = json.dumps(value, ensure_ascii=False)
                else:
                    properties[key] = value

        feature = {
            'type': 'Feature',
            'geometry': geometry,
            'properties': properties
        }

        # Add id if available
        if 'id' in item:
            feature['id'] = item['id']

        features.append(feature)

    if not features:
        log.warning(f"No valid geometries found in {len(data)} records")
        return None

    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    log.info(f"Transformed {len(features)} records to GeoJSON (skipped {skipped} without geometry)")

    return geojson


def has_geometry_data(
    data: List[Dict[str, Any]],
    geometry_field: str
) -> bool:
    """
    Check if data contains valid geometry.

    Args:
        data: List of data items
        geometry_field: Field name to check

    Returns:
        True if at least one item has valid geometry
    """
    if not data or not geometry_field:
        return False

    for item in data:
        if extract_geometry(item, geometry_field) is not None:
            return True

    return False
