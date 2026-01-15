"""CKAN API Client"""

import logging
from typing import Any, Dict, List, Optional

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from .logger import get_logger

log = get_logger("cms_ckan_sync.ckan_client")


class CKANError(Exception):
    """CKAN API error"""
    pass


class CKANClient:
    """
    Client for CKAN Action API.

    Handles dataset creation, resource upload, and error handling.
    """

    def __init__(
        self,
        url: str,
        api_token: str,
        organization: str,
        timeout: int = 60
    ):
        """
        Initialize CKAN client.

        Args:
            url: CKAN instance URL
            api_token: CKAN API token
            organization: Default organization ID
            timeout: Request timeout in seconds
        """
        self.url = url.rstrip('/')
        self.api_token = api_token
        self.organization = organization
        self.timeout = timeout

        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': api_token,
            'Content-Type': 'application/json'
        })

    def _api_url(self, action: str) -> str:
        """Get full API URL for an action"""
        return f"{self.url}/api/3/action/{action}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.Timeout, requests.exceptions.ConnectionError))
    )
    def _call_api(
        self,
        action: str,
        data: Optional[Dict[str, Any]] = None,
        method: str = 'POST'
    ) -> Dict[str, Any]:
        """
        Call a CKAN API action.

        Args:
            action: API action name
            data: Request data
            method: HTTP method

        Returns:
            Result from API response

        Raises:
            CKANError: If the request fails
        """
        url = self._api_url(action)
        log.debug(f"CKAN API {method} {action}")

        try:
            if method == 'GET':
                response = self.session.get(url, params=data, timeout=self.timeout)
            else:
                response = self.session.post(url, json=data, timeout=self.timeout)

            result = response.json()

            if not result.get('success'):
                error = result.get('error', {})
                if isinstance(error, dict):
                    error_msg = error.get('message', str(error))
                else:
                    error_msg = str(error)
                raise CKANError(f"CKAN API error: {error_msg}")

            return result.get('result', {})

        except requests.exceptions.Timeout:
            log.error(f"Request timeout: {url}")
            raise
        except requests.exceptions.ConnectionError as e:
            log.error(f"Connection error: {url} - {e}")
            raise
        except requests.exceptions.RequestException as e:
            log.error(f"Request error: {url} - {e}")
            if hasattr(e, 'response') and e.response is not None:
                log.error(f"Response: {e.response.text[:500]}")
            raise CKANError(f"Request failed: {e}")

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get dataset by ID or name.

        Args:
            dataset_id: Dataset ID or name

        Returns:
            Dataset data or None if not found
        """
        try:
            return self._call_api('package_show', {'id': dataset_id}, method='GET')
        except CKANError as e:
            # Handle "Not Found" error in various languages
            # English: "not found", Japanese: "見つかりません"
            error_str = str(e)
            if 'not found' in error_str.lower() or '見つかりません' in error_str:
                return None
            raise

    def create_dataset(self, dataset_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new dataset.

        Args:
            dataset_info: Dataset information

        Returns:
            Created dataset data
        """
        log.info(f"Creating dataset: {dataset_info.get('name')}")
        return self._call_api('package_create', dataset_info)

    def update_dataset(self, dataset_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing dataset.

        Args:
            dataset_info: Dataset information (must include 'id')

        Returns:
            Updated dataset data
        """
        log.info(f"Updating dataset: {dataset_info.get('id') or dataset_info.get('name')}")
        return self._call_api('package_update', dataset_info)

    def create_or_update_dataset(
        self,
        dataset_id: str,
        dataset_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create dataset if not exists, update if exists.

        Args:
            dataset_id: Dataset ID/name
            dataset_info: Dataset information

        Returns:
            Dataset data
        """
        existing = self.get_dataset(dataset_id)

        if existing:
            # Update existing dataset
            dataset_info['id'] = existing['id']
            # Preserve existing resources
            if 'resources' not in dataset_info:
                dataset_info['resources'] = existing.get('resources', [])
            return self.update_dataset(dataset_info)
        else:
            # Create new dataset
            dataset_info['name'] = dataset_id
            return self.create_dataset(dataset_info)

    def get_dataset_resources(self, dataset_id: str) -> List[Dict[str, Any]]:
        """
        Get all resources for a dataset.

        Args:
            dataset_id: Dataset ID or name

        Returns:
            List of resources
        """
        dataset = self.get_dataset(dataset_id)
        if dataset:
            return dataset.get('resources', [])
        return []

    def delete_resource(self, resource_id: str) -> None:
        """
        Delete a resource.

        Args:
            resource_id: Resource ID
        """
        log.info(f"Deleting resource: {resource_id}")
        self._call_api('resource_delete', {'id': resource_id})

    def delete_resources_by_name(self, dataset_id: str, resource_names: List[str]) -> int:
        """
        Delete resources by name from a dataset.

        Args:
            dataset_id: Dataset ID or name
            resource_names: List of resource names to delete

        Returns:
            Number of resources deleted
        """
        resources = self.get_dataset_resources(dataset_id)
        deleted = 0

        for resource in resources:
            if resource.get('name') in resource_names:
                try:
                    self.delete_resource(resource['id'])
                    deleted += 1
                except CKANError as e:
                    log.warning(f"Failed to delete resource {resource['name']}: {e}")

        return deleted

    def upload_resource(
        self,
        package_id: str,
        name: str,
        content: bytes,
        format: str,
        description: str = '',
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a resource to a dataset.

        Args:
            package_id: Dataset ID
            name: Resource name
            content: File content as bytes
            format: File format (CSV, JSON, GeoJSON, etc.)
            description: Resource description
            mime_type: MIME type (auto-detected if not provided)

        Returns:
            Created resource data
        """
        log.info(f"Uploading resource: {name}.{format.lower()} to dataset {package_id}")

        # Determine MIME type
        if mime_type is None:
            mime_types = {
                'csv': 'text/csv',
                'json': 'application/json',
                'geojson': 'application/geo+json',
                'xml': 'application/xml',
            }
            mime_type = mime_types.get(format.lower(), 'application/octet-stream')

        # Prepare form data
        resource_data = {
            'package_id': package_id,
            'name': name,
            'description': description,
            'format': format.upper()
        }

        # Prepare file
        filename = f"{name}.{format.lower()}"
        files = {
            'upload': (filename, content, mime_type)
        }

        url = self._api_url('resource_create')

        try:
            # Note: Don't use Content-Type header for multipart
            headers = {'Authorization': self.api_token}
            response = requests.post(
                url,
                data=resource_data,
                files=files,
                headers=headers,
                timeout=self.timeout
            )

            result = response.json()

            if not result.get('success'):
                error = result.get('error', {})
                raise CKANError(f"Resource upload failed: {error}")

            resource_result = result.get('result', {})
            log.info(f"Resource uploaded successfully: {resource_result['id']}")

            # Trigger DataPusher to update DataStore
            self.trigger_datapusher(resource_result['id'])

            return resource_result

        except requests.exceptions.RequestException as e:
            log.error(f"Resource upload error: {e}")
            raise CKANError(f"Resource upload failed: {e}")

    def test_connection(self) -> bool:
        """
        Test CKAN connection.

        Returns:
            True if connection successful
        """
        try:
            result = self._call_api('status_show', method='GET')
            return bool(result)
        except Exception as e:
            log.error(f"Connection test failed: {e}")
            return False

    def trigger_datapusher(self, resource_id: str) -> bool:
        """
        Trigger DataPusher to update DataStore for a resource.

        This ensures the DataStore is refreshed after resource upload/update,
        so the data is immediately available for API queries and preview.

        Args:
            resource_id: Resource ID to trigger DataPusher for

        Returns:
            True if trigger successful, False otherwise
        """
        try:
            log.info(f"Triggering DataPusher for resource: {resource_id}")
            self._call_api('datapusher_submit', {'resource_id': resource_id})
            log.info(f"DataPusher triggered successfully for resource: {resource_id}")
            return True
        except CKANError as e:
            # DataPusher might not be available or configured - log warning but don't fail
            log.warning(f"DataPusher trigger failed (non-fatal): {e}")
            return False
        except Exception as e:
            log.warning(f"DataPusher trigger error (non-fatal): {e}")
            return False

    def get_organization(self, org_id: str) -> Optional[Dict[str, Any]]:
        """
        Get organization by ID.

        Args:
            org_id: Organization ID or name

        Returns:
            Organization data or None
        """
        try:
            return self._call_api('organization_show', {'id': org_id}, method='GET')
        except CKANError:
            return None

    def list_datasets(self, organization: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List datasets, optionally filtered by organization.

        Args:
            organization: Organization ID to filter by (uses default if not provided)

        Returns:
            List of dataset dictionaries with id, name, title
        """
        org = organization or self.organization
        try:
            # Use package_search with organization filter
            result = self._call_api(
                'package_search',
                {'fq': f'organization:{org}', 'rows': 1000},
                method='GET'
            )
            datasets = result.get('results', [])
            # Return simplified list
            return [
                {
                    'id': ds.get('id'),
                    'name': ds.get('name'),
                    'title': ds.get('title', ds.get('name')),
                    'num_resources': ds.get('num_resources', 0)
                }
                for ds in datasets
            ]
        except CKANError as e:
            log.error(f"Failed to list datasets: {e}")
            return []

    def list_resources(self, dataset_id: str) -> List[Dict[str, Any]]:
        """
        List resources for a dataset.

        Args:
            dataset_id: Dataset ID or name

        Returns:
            List of resource dictionaries with id, name, format, url
        """
        try:
            dataset = self.get_dataset(dataset_id)
            if not dataset:
                return []
            resources = dataset.get('resources', [])
            return [
                {
                    'id': res.get('id'),
                    'name': res.get('name'),
                    'format': res.get('format'),
                    'url': res.get('url'),
                    'size': res.get('size'),
                    'last_modified': res.get('last_modified')
                }
                for res in resources
            ]
        except CKANError as e:
            log.error(f"Failed to list resources for {dataset_id}: {e}")
            return []

    def find_resource_by_name(
        self,
        dataset_id: str,
        name: str,
        format: str = 'CSV'
    ) -> Optional[Dict[str, Any]]:
        """
        Find a resource by exact name and format match.

        Args:
            dataset_id: Dataset ID or name
            name: Exact resource name to find
            format: Resource format (default: CSV)

        Returns:
            Resource dict if found, None otherwise
        """
        try:
            resources = self.get_dataset_resources(dataset_id)
            for r in resources:
                # Strict match: exact name (case-insensitive) and format
                if (r.get('name', '').lower() == name.lower() and
                    r.get('format', '').upper() == format.upper()):
                    log.debug(f"Found resource: {r.get('id')} (name={name}, format={format})")
                    return r
            log.debug(f"Resource not found: name={name}, format={format} in dataset {dataset_id}")
            return None
        except CKANError as e:
            log.warning(f"Error finding resource in {dataset_id}: {e}")
            return None

    def update_resource(
        self,
        resource_id: str,
        content: bytes,
        name: Optional[str] = None,
        format: Optional[str] = None,
        description: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing resource with new content.

        Args:
            resource_id: Resource ID to update
            content: New file content as bytes
            name: New name (optional)
            format: File format (optional)
            description: New description (optional)
            mime_type: MIME type (auto-detected if not provided)

        Returns:
            Updated resource data
        """
        log.info(f"Updating resource: {resource_id}")

        # First get the existing resource info
        try:
            existing = self._call_api('resource_show', {'id': resource_id}, method='GET')
        except CKANError as e:
            raise CKANError(f"Resource not found: {resource_id}")

        # Use existing values if not provided
        if name is None:
            name = existing.get('name', 'data')
        if format is None:
            format = existing.get('format', 'CSV')
        if description is None:
            description = existing.get('description', '')

        # Determine MIME type
        if mime_type is None:
            mime_types = {
                'csv': 'text/csv',
                'json': 'application/json',
                'geojson': 'application/geo+json',
                'xml': 'application/xml',
            }
            mime_type = mime_types.get(format.lower(), 'application/octet-stream')

        # Prepare form data for update
        resource_data = {
            'id': resource_id,
            'name': name,
            'description': description,
            'format': format.upper()
        }

        # Prepare file
        filename = f"{name}.{format.lower()}"
        files = {
            'upload': (filename, content, mime_type)
        }

        url = self._api_url('resource_update')

        try:
            headers = {'Authorization': self.api_token}
            response = requests.post(
                url,
                data=resource_data,
                files=files,
                headers=headers,
                timeout=self.timeout
            )

            result = response.json()

            if not result.get('success'):
                error = result.get('error', {})
                raise CKANError(f"Resource update failed: {error}")

            log.info(f"Resource updated successfully: {resource_id}")

            # Trigger DataPusher to update DataStore
            self.trigger_datapusher(resource_id)

            return result.get('result', {})

        except requests.exceptions.RequestException as e:
            log.error(f"Resource update error: {e}")
            raise CKANError(f"Resource update failed: {e}")
