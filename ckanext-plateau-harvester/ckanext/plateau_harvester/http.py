"""
HTTP client for interacting with PLATEAU APIs (REST and GraphQL)
"""
import json
import logging
import time
from typing import Dict, Any, Optional

import requests

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
USER_AGENT = 'CKAN-PLATEAU-Harvester/0.1'


class HttpClient:
    """
    Generic HTTP client supporting both REST and GraphQL APIs
    """

    def __init__(
        self,
        api_base: str,
        api_key: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize HTTP client

        Args:
            api_base: Base URL for the API (e.g., "https://api.example.com/v1/")
            api_key: Optional API key for authentication
            extra_headers: Optional additional headers
        """
        self.api_base = api_base.rstrip('/') + '/'
        self.api_key = api_key
        self.headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'application/json',
        }
        if extra_headers:
            self.headers.update(extra_headers)

    def _auth(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Add authentication headers if API key is provided"""
        h = dict(headers)
        if self.api_key:
            # Adjust based on actual API requirements
            # Some APIs use X-API-Key, others use Authorization: Bearer
            h['X-API-Key'] = self.api_key
        return h

    def get(
        self,
        path_or_url: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform GET request

        Args:
            path_or_url: Either a full URL or a path relative to api_base
            params: Optional query parameters

        Returns:
            Parsed JSON response
        """
        url = path_or_url if path_or_url.startswith('http') else self.api_base + path_or_url.lstrip('/')

        log.debug(f'GET {url} with params: {params}')

        r = requests.get(
            url,
            params=params,
            headers=self._auth(self.headers),
            timeout=DEFAULT_TIMEOUT
        )
        r.raise_for_status()
        return r.json()

    def post_json(
        self,
        path_or_url: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform POST request with JSON payload

        Args:
            path_or_url: Either a full URL or a path relative to api_base
            payload: JSON data to send

        Returns:
            Parsed JSON response
        """
        url = path_or_url if path_or_url.startswith('http') else self.api_base + path_or_url.lstrip('/')

        headers = self._auth({**self.headers, 'Content-Type': 'application/json'})

        log.debug(f'POST {url}')

        r = requests.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            timeout=DEFAULT_TIMEOUT
        )
        r.raise_for_status()
        return r.json()

    def graphql(
        self,
        path_or_url: str,
        query: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform GraphQL query

        Args:
            path_or_url: GraphQL endpoint (full URL or relative path)
            query: GraphQL query string
            variables: Optional query variables

        Returns:
            Parsed JSON response
        """
        payload = {
            'query': query,
            'variables': variables or {}
        }

        log.debug(f'GraphQL query to {path_or_url}')

        return self.post_json(path_or_url, payload)
