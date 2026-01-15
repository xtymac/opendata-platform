"""
PLATEAU Harvester implementation

Implements the three-stage harvest process:
1. Gather: Collect identifiers from the remote source
2. Fetch: Retrieve full metadata for each identifier
3. Import: Create/update CKAN packages
"""
import json
import logging
from typing import Any, Dict, List, Optional

from ckan.plugins import toolkit
from ckanext.harvest.harvesters.base import HarvesterBase
from ckanext.harvest.model import HarvestObject

from .http import HttpClient
from .mapping import to_package_dict

log = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 100


class PlateauHarvester(HarvesterBase):
    """
    PLATEAU Harvester supporting both REST and GraphQL APIs

    Source configuration (JSON in Harvest Source "Configuration" field):
    {
      "api_base": "https://api.example.com/v1/",
      "api_key": "<optional>",
      "mode": "rest",  # or "graphql"

      # REST mode settings
      "list_path": "datasets",
      "detail_path": "datasets/{id}",

      # GraphQL mode settings
      "graph_path": "graphql",
      "list_query": "query($q:String,$after:String){ datasets(...) }",
      "detail_query": "query($id:ID!){ dataset(id:$id){ ... }}",

      # Common settings
      "search": "keyword",
      "page_size": 100,
      "owner_org": "org-name-or-id",
      "extra_headers": {"User-Agent": "Custom"}
    }
    """

    def info(self) -> Dict[str, Any]:
        """Return harvester info"""
        return {
            'name': 'plateau',
            'title': 'PLATEAU / 3D都市モデル',
            'description': 'Harvest PLATEAU 3D city model datasets via REST or GraphQL APIs'
        }

    def _client(self, config: Dict[str, Any]) -> HttpClient:
        """Create HTTP client from config"""
        return HttpClient(
            api_base=config.get('api_base', ''),
            api_key=config.get('api_key'),
            extra_headers=config.get('extra_headers')
        )

    # ========== GATHER STAGE ==========

    def gather_stage(self, harvest_job):
        """
        Gather identifiers from the remote source

        Returns:
            List of HarvestObject IDs
        """
        log.info('Starting gather stage for source: %s', harvest_job.source.id)

        source_config = self._get_source_config(harvest_job)
        client = self._client(source_config)
        mode = source_config.get('mode', 'rest')

        ids: List[str] = []

        try:
            if mode == 'graphql':
                ids = self._gather_graphql(client, source_config)
            else:
                ids = self._gather_rest(client, source_config)
        except Exception as e:
            self._save_gather_error(f'Gather failed: {str(e)}', harvest_job)
            return []

        log.info('Gathered %d dataset IDs', len(ids))

        if not ids:
            log.warning('No datasets found')
            return []

        # Create HarvestObject for each ID
        object_ids = []
        for guid in ids:
            obj = HarvestObject(guid=guid, job=harvest_job)
            obj.save()
            object_ids.append(obj.id)

        return object_ids

    def _gather_rest(self, client: HttpClient, config: Dict[str, Any]) -> List[str]:
        """Gather using REST API pagination"""
        list_path = config.get('list_path', 'datasets')
        page_size = int(config.get('page_size', DEFAULT_PAGE_SIZE))
        search = config.get('search')

        ids = []
        page = 1

        while True:
            params = {
                'page': page,
                'page_size': page_size,
            }
            if search:
                params['q'] = search

            log.debug(f'Fetching page {page}')

            data = client.get(list_path, params)

            # Handle different response structures
            items = data.get('results') or data.get('items') or data.get('data') or []

            for item in items:
                item_id = item.get('id')
                if item_id:
                    ids.append(str(item_id))

            # Check if there are more pages
            if len(items) < page_size:
                break

            # Some APIs provide total/hasNext
            if data.get('hasNext') is False:
                break

            page += 1

        return ids

    def _gather_graphql(self, client: HttpClient, config: Dict[str, Any]) -> List[str]:
        """Gather using GraphQL cursor pagination"""
        graph_path = config.get('graph_path', 'graphql')
        query = config.get('list_query')

        if not query:
            raise Exception('Missing list_query for GraphQL mode')

        ids = []
        variables = {
            'q': config.get('search'),
            'after': None
        }

        while True:
            log.debug(f'GraphQL query with cursor: {variables.get("after")}')

            data = client.graphql(graph_path, query, variables)

            # Handle GraphQL response structure
            # Adjust based on actual API schema
            datasets = data.get('data', {}).get('datasets', {})
            nodes = datasets.get('nodes', [])

            for node in nodes:
                node_id = node.get('id')
                if node_id:
                    ids.append(str(node_id))

            # Check pagination
            page_info = datasets.get('pageInfo', {})
            if page_info.get('hasNextPage'):
                variables['after'] = page_info.get('endCursor')
            else:
                break

        return ids

    # ========== FETCH STAGE ==========

    def fetch_stage(self, harvest_object):
        """
        Fetch full metadata for a single object

        Returns:
            True if successful, False otherwise
        """
        log.debug('Fetching object: %s', harvest_object.guid)

        source_config = self._get_source_config(harvest_object)
        client = self._client(source_config)
        mode = source_config.get('mode', 'rest')
        guid = harvest_object.guid

        try:
            if mode == 'graphql':
                item = self._fetch_graphql(client, source_config, guid)
            else:
                item = self._fetch_rest(client, source_config, guid)

            harvest_object.content = json.dumps(item)
            harvest_object.save()
            return True

        except Exception as e:
            self._save_object_error(f'Fetch failed: {str(e)}', harvest_object)
            return False

    def _fetch_rest(self, client: HttpClient, config: Dict[str, Any], guid: str) -> Dict[str, Any]:
        """Fetch detail using REST API"""
        detail_tpl = config.get('detail_path', 'datasets/{id}')
        path = detail_tpl.format(id=guid)

        return client.get(path)

    def _fetch_graphql(self, client: HttpClient, config: Dict[str, Any], guid: str) -> Dict[str, Any]:
        """Fetch detail using GraphQL"""
        graph_path = config.get('graph_path', 'graphql')
        query = config.get('detail_query')

        if not query:
            raise Exception('Missing detail_query for GraphQL mode')

        data = client.graphql(graph_path, query, {'id': guid})

        # Extract dataset from GraphQL response
        return data.get('data', {}).get('dataset') or {}

    # ========== IMPORT STAGE ==========

    def import_stage(self, harvest_object):
        """
        Create or update CKAN package from harvested metadata

        Returns:
            True if successful, False otherwise
        """
        log.debug('Importing object: %s', harvest_object.guid)

        source_config = self._get_source_config(harvest_object)
        owner_org = source_config.get('owner_org')

        # Parse harvested content
        try:
            item = json.loads(harvest_object.content)
        except Exception as e:
            self._save_object_error(f'Invalid JSON content: {str(e)}', harvest_object)
            return False

        if not item:
            self._save_object_error('Empty content', harvest_object)
            return False

        # Map to CKAN package dict
        try:
            pkg_dict = to_package_dict(item)
        except Exception as e:
            self._save_object_error(f'Mapping failed: {str(e)}', harvest_object)
            return False

        # Set owner org
        if owner_org:
            pkg_dict['owner_org'] = owner_org

        # Create or update package
        context = {
            'user': self._get_user_name(),
            'ignore_auth': True
        }

        # Check if package already exists
        existing = None
        try:
            existing = toolkit.get_action('package_show')(context, {'id': pkg_dict['name']})
        except toolkit.ObjectNotFound:
            existing = None

        try:
            if existing:
                # Update existing package
                pkg_dict['id'] = existing['id']
                toolkit.get_action('package_update')(context, pkg_dict)
                log.info('Updated package: %s', pkg_dict['name'])
            else:
                # Create new package
                toolkit.get_action('package_create')(context, pkg_dict)
                log.info('Created package: %s', pkg_dict['name'])

            return True

        except Exception as e:
            self._save_object_error(f'Package create/update failed: {str(e)}', harvest_object)
            return False

    # ========== HELPER METHODS ==========

    def _get_user_name(self) -> str:
        """Get site user for performing actions"""
        context = {'ignore_auth': True}
        site_user = toolkit.get_action('get_site_user')(context, {})
        return site_user['name']

    def _get_source_config(self, obj_or_job) -> Dict[str, Any]:
        """Parse source configuration JSON"""
        raw = obj_or_job.source.config or '{}'
        try:
            return json.loads(raw)
        except Exception:
            log.error('Invalid source config JSON: %s', raw)
            return {}
