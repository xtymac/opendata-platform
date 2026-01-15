from __future__ import annotations

from typing import Any, Dict, List, Optional

import ckan.plugins as p
import ckan.plugins.toolkit as toolkit


_ignore_missing = toolkit.get_validator('ignore_missing')
_int_validator = toolkit.get_validator('natural_number_validator')
_default = toolkit.get_validator('default')


class SimpleMapView(p.SingletonPlugin):
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)

    def update_config(self, config: Dict[str, Any]):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')
        toolkit.add_resource('assets', 'ckanext-simplemap')

    # IResourceView -----------------------------------------------------

    def info(self) -> Dict[str, Any]:
        return {
            'name': 'simple_map',
            'title': toolkit._('Map'),
            'icon': 'map-marker-alt',
            'requires_datastore': True,
            'default_title': toolkit._('Map'),
            'preview_enabled': False,
            'schema': {
                'latitude_field': [_ignore_missing],
                'longitude_field': [_ignore_missing],
                'label_field': [_ignore_missing],
                'limit': [_default(1000), _int_validator],
            },
        }

    def can_view(self, data_dict: Dict[str, Any]) -> bool:
        resource = data_dict['resource']
        return resource.get('datastore_active') is True

    def setup_template_variables(
        self, context: Dict[str, Any], data_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        resource = data_dict['resource']
        view = data_dict.get('resource_view', {})

        lat_field = view.get('latitude_field')
        lon_field = view.get('longitude_field')
        label_field = view.get('label_field')
        limit = int(view.get('limit') or 1000)

        fields = self._get_datastore_fields(resource['id'])

        # Try to auto-detect lat/lon fields if not already set
        if not lat_field or not lon_field:
            guessed_lat, guessed_lon = self._guess_lat_lon(fields)
            lat_field = lat_field or guessed_lat
            lon_field = lon_field or guessed_lon

        field_options = [
            {'value': f['id'], 'text': f['id']}
            for f in fields
            if f.get('id')
        ]

        return {
            'fields': fields,
            'field_options': field_options,
            'lat_field': lat_field,
            'lon_field': lon_field,
            'label_field': label_field,
            'limit': limit,
            'site_url': toolkit.config.get('ckan.site_url', ''),
        }

    def view_template(self, context: Dict[str, Any], data_dict: Dict[str, Any]):
        return 'simplemap/view.html'

    def form_template(self, context: Dict[str, Any], data_dict: Dict[str, Any]):
        return 'simplemap/form.html'

    # Helpers -----------------------------------------------------------

    def _get_datastore_fields(self, resource_id: str) -> List[Dict[str, Any]]:
        try:
            action = toolkit.get_action('datastore_search')
            result = action(
                {'ignore_auth': True},
                {'resource_id': resource_id, 'limit': 0},
            )
            return [f for f in result.get('fields', []) if f.get('id') != '_id']
        except Exception:  # pragma: no cover - we fallback to empty list
            return []

    def _guess_lat_lon(
        self, fields: List[Dict[str, Any]]
    ) -> tuple[Optional[str], Optional[str]]:
        lat_candidates = ('latitude', 'lat', 'y')
        lon_candidates = (
            'longitude',
            'lon',
            'lng',
            'long',
            'x',
        )
        normalised = {f['id'].lower(): f['id'] for f in fields if 'id' in f}

        lat_field = next(
            (normalised[name] for name in lat_candidates if name in normalised),
            None,
        )
        lon_field = next(
            (normalised[name] for name in lon_candidates if name in normalised),
            None,
        )

        return lat_field, lon_field
