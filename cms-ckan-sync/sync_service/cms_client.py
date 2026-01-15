"""Re:Earth CMS API Client"""

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

log = get_logger("cms_ckan_sync.cms_client")


class CMSError(Exception):
    """CMS API error"""
    pass


class CMSClient:
    """
    Client for Re:Earth CMS Public API.

    Handles pagination and error handling for CMS API requests.
    Supports both Public API (no auth) and Integration API (with token).
    """

    def __init__(self, base_url: str, api_token: str = None, timeout: int = 30):
        """
        Initialize CMS client.

        Args:
            base_url: CMS API base URL (e.g., https://api.cms.reearth.io/api/p/{workspace}/{project})
            api_token: Optional API token (not needed for public projects)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.timeout = timeout

        # Setup session with default headers
        self.session = requests.Session()
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        # Only add Authorization header if token is provided
        if api_token:
            headers['Authorization'] = f'Bearer {api_token}'
        self.session.headers.update(headers)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.Timeout, requests.exceptions.ConnectionError))
    )
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an API request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            data: Request body data

        Returns:
            Response data as dictionary

        Raises:
            CMSError: If the request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        log.debug(f"CMS API {method} {url}")

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=self.timeout
            )

            # Check for errors
            if response.status_code == 401:
                raise CMSError("Authentication failed. Check your API token.")
            elif response.status_code == 403:
                raise CMSError("Access forbidden. Check your permissions.")
            elif response.status_code == 404:
                raise CMSError(f"Resource not found: {endpoint}")
            elif response.status_code >= 500:
                raise CMSError(f"CMS server error: {response.status_code}")

            response.raise_for_status()

            return response.json()

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
            raise CMSError(f"Request failed: {e}")

    def fetch_model_items(
        self,
        model_id: str,
        page: int = 1,
        per_page: int = 100
    ) -> Dict[str, Any]:
        """
        Fetch items from a CMS model.

        Args:
            model_id: Model identifier
            page: Page number (1-based)
            per_page: Items per page

        Returns:
            Response containing results and pagination info
        """
        log.info(f"Fetching items from model: {model_id} (page={page}, per_page={per_page})")

        params = {
            'page': page,
            'perPage': per_page
        }

        # Public API format: {base_url}/{model_key}
        return self._request('GET', model_id, params=params)

    def fetch_all_items(self, model_id: str, per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch all items from a CMS model with pagination.

        Args:
            model_id: Model identifier
            per_page: Items per page

        Returns:
            List of all items from the model
        """
        all_items = []
        page = 1

        while True:
            response = self.fetch_model_items(model_id, page=page, per_page=per_page)

            results = response.get('results', [])
            all_items.extend(results)

            total_count = response.get('totalCount', len(results))
            log.debug(f"Fetched page {page}: {len(results)} items (total: {total_count})")

            # Check if there are more pages
            if len(all_items) >= total_count or len(results) < per_page:
                break

            page += 1

        log.info(f"Fetched {len(all_items)} total items from model: {model_id}")
        return all_items

    def get_model_schema(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get schema information for a model (if available).

        Args:
            model_id: Model identifier

        Returns:
            Schema information or None if not available
        """
        try:
            # Try to fetch schema endpoint (may not be available in all CMS versions)
            return self._request('GET', model_id)
        except CMSError:
            log.debug(f"Schema not available for model: {model_id}")
            return None

    def fetch_csv(self, model_id: str) -> str:
        """
        Fetch CSV data directly from CMS.

        This preserves the original column order as defined in the CMS schema.

        Args:
            model_id: Model identifier

        Returns:
            CSV content as string

        Raises:
            CMSError: If the request fails
        """
        url = f"{self.base_url}/{model_id}.csv"
        log.info(f"Fetching CSV from CMS: {url}")

        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                headers={'Accept': 'text/csv'}
            )

            if response.status_code == 404:
                raise CMSError(f"CSV export not found: {model_id}")
            elif response.status_code >= 400:
                raise CMSError(f"Failed to fetch CSV: {response.status_code}")

            response.raise_for_status()

            # Ensure UTF-8 encoding
            content = response.content.decode('utf-8')
            lines = content.strip().split('\n')
            log.info(f"Fetched CSV with {len(lines) - 1} records from model: {model_id}")

            return content

        except requests.exceptions.RequestException as e:
            log.error(f"CSV fetch error: {url} - {e}")
            raise CMSError(f"Failed to fetch CSV: {e}")

    def test_connection(self) -> bool:
        """
        Test the CMS connection.

        Returns:
            True if connection is successful
        """
        try:
            # Try to make a simple request
            # This might need adjustment based on available endpoints
            response = self.session.get(
                self.base_url,
                timeout=self.timeout
            )
            return response.status_code < 500
        except Exception as e:
            log.error(f"Connection test failed: {e}")
            return False
