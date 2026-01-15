# -*- coding: utf-8 -*-

"""FIWARE Orion Context Broker harvester implementation."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from requests import RequestException, Response, Session

from ckantoolkit import config as toolkit_config

from ckanext.harvest.harvesters.base import HarvesterBase
from ckanext.harvest.model import HarvestObject

log = logging.getLogger(__name__)

DEFAULT_ORION_URL = "http://orion:1026"
DEFAULT_API_VERSION = "v2"  # "v2" for NGSI-v2, "ngsi-ld/v1" for NGSI-LD
REQUEST_TIMEOUT = 30  # seconds
DEFAULT_ENTITY_LIMIT = 100


class FiwareOrionHarvester(HarvesterBase):
    """Harvester for FIWARE Orion Context Broker using NGSI APIs."""

    def info(self) -> Dict[str, str]:
        return {
            "name": "fiware_orion",
            "title": "FIWARE Orion Context Broker",
            "description": "Harvest context entities from FIWARE Orion Context Broker (NGSI v2 / NGSI-LD).",
        }

    def validate_config(self, config: str) -> str:
        """Validate harvester configuration."""
        if not config:
            return config

        try:
            config_obj = json.loads(config)

            # Validate API version
            api_version = config_obj.get("api_version", DEFAULT_API_VERSION)
            if api_version not in ["v2", "ngsi-ld/v1"]:
                raise ValueError(f"Invalid api_version: {api_version}. Must be 'v2' or 'ngsi-ld/v1'")

            return config
        except ValueError as e:
            raise ValueError(f"Invalid JSON configuration: {e}")

    # ------------------------------------------------------------------
    # Gather stage
    # ------------------------------------------------------------------
    def gather_stage(self, harvest_job) -> List[str]:
        log.info("Starting FIWARE Orion gather stage (source=%s)", harvest_job.source.url)

        try:
            config = self._load_config(harvest_job.source.config, harvest_job.source.url)
        except ValueError as err:
            message = f"Failed to parse harvest source config: {err}"
            log.error(message)
            self._save_gather_error(message, harvest_job)
            return []

        session = self._get_http_session(config)

        # Get list of entities from Orion
        object_ids: List[str] = []
        offset = 0
        limit = config.get("entity_limit", DEFAULT_ENTITY_LIMIT)

        while True:
            try:
                entities = self._fetch_entities(session, config, offset, limit)
            except Exception as err:
                message = f"Failed to fetch entities (offset={offset}): {err}"
                log.exception(message)
                self._save_gather_error(message, harvest_job)
                return object_ids

            if not entities:
                log.info("No more entities to harvest")
                break

            for entity in entities:
                entity_id = entity.get("id")
                if not entity_id:
                    log.warning("Skipped entity without id: %r", entity)
                    continue

                # Use entity id as the unique identifier
                harvest_object = HarvestObject(guid=entity_id, job=harvest_job)
                harvest_object.save()
                object_ids.append(harvest_object.id)
                log.debug("Gathered entity: %s (type=%s)", entity_id, entity.get("type"))

            # Check if we've fetched all entities
            if len(entities) < limit:
                log.info("Reached final page (offset=%s)", offset)
                break

            offset += limit

        log.info("Gathered %d entities from Orion Context Broker", len(object_ids))
        return object_ids

    # ------------------------------------------------------------------
    # Fetch stage
    # ------------------------------------------------------------------
    def fetch_stage(self, harvest_object) -> bool:
        log.info("Fetching FIWARE entity (id=%s)", harvest_object.guid)

        try:
            config = self._load_config(harvest_object.source.config, harvest_object.source.url)
        except ValueError as err:
            message = f"Failed to parse harvest source config: {err}"
            log.error(message)
            self._save_object_error(message, harvest_object, "Fetch")
            return False

        session = self._get_http_session(config)

        try:
            entity = self._fetch_entity_by_id(session, config, harvest_object.guid)
        except Exception as err:
            message = f"Failed to fetch entity {harvest_object.guid}: {err}"
            log.exception(message)
            self._save_object_error(message, harvest_object, "Fetch")
            return False

        if not entity:
            message = f"Entity {harvest_object.guid} not found"
            log.error(message)
            self._save_object_error(message, harvest_object, "Fetch")
            return False

        # Store the full entity as JSON
        harvest_object.content = json.dumps(entity)
        harvest_object.save()
        return True

    # ------------------------------------------------------------------
    # Import stage
    # ------------------------------------------------------------------
    def import_stage(self, harvest_object) -> bool:
        log.info("Importing FIWARE entity (id=%s)", harvest_object.guid)

        if not harvest_object.content:
            message = f"No content to import for object {harvest_object.id}"
            log.error(message)
            self._save_object_error(message, harvest_object, "Import")
            return False

        try:
            entity = json.loads(harvest_object.content)
        except ValueError as err:
            message = f"Entity JSON could not be decoded: {err}"
            log.error(message)
            self._save_object_error(message, harvest_object, "Import")
            return False

        try:
            config = self._load_config(harvest_object.source.config, harvest_object.source.url)
            package_dict = self._entity_to_package(entity, harvest_object, config)
        except Exception as err:
            message = f"Failed to map entity {harvest_object.guid} to CKAN package: {err}"
            log.exception(message)
            self._save_object_error(message, harvest_object, "Import")
            return False

        # Ensure we have a valid package name
        package_dict.setdefault(
            "name",
            self._gen_new_name(package_dict.get("title") or harvest_object.guid),
        )
        package_dict.setdefault("id", harvest_object.guid)

        return self._create_or_update_package(package_dict, harvest_object)

    def _create_or_update_package(
        self,
        package_dict: Dict[str, Any],
        harvest_object: HarvestObject
    ) -> bool:
        """Create or update a CKAN package (dataset) from harvested data."""
        from ckan import model
        from ckan.logic import get_action, ValidationError
        from ckan.plugins import toolkit

        # Create context
        context = {
            'model': model,
            'session': model.Session,
            'user': self._get_user_name(),
            'ignore_auth': True,
        }

        # Check if package already exists
        package_id = package_dict.get('id')
        try:
            existing_package = get_action('package_show')(context, {'id': package_id})
            # Package exists, update it
            package_dict['id'] = existing_package['id']
            try:
                updated_package = get_action('package_update')(context, package_dict)
                harvest_object.package_id = updated_package['id']
                harvest_object.current = True
                harvest_object.save()
                log.info(f"Updated package {package_id}")
                return True
            except ValidationError as e:
                self._save_object_error(f'Validation Error: {e.error_dict}', harvest_object, 'Import')
                return False
        except toolkit.ObjectNotFound:
            # Package doesn't exist, create it
            try:
                # Remove id from dict for creation
                if 'id' in package_dict:
                    del package_dict['id']

                new_package = get_action('package_create')(context, package_dict)
                harvest_object.package_id = new_package['id']
                harvest_object.current = True
                harvest_object.save()
                log.info(f"Created package {new_package['id']}")
                return True
            except ValidationError as e:
                self._save_object_error(f'Validation Error: {e.error_dict}', harvest_object, 'Import')
                return False
        except Exception as e:
            self._save_object_error(f'Error creating/updating package: {e}', harvest_object, 'Import')
            return False

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def _load_config(self, raw_config: Optional[str], source_url: str) -> Dict[str, Any]:
        """Load and validate configuration."""
        if not raw_config:
            config: Dict[str, Any] = {}
        else:
            try:
                config = json.loads(raw_config)
            except ValueError as err:
                raise ValueError(f"Invalid JSON: {err}") from err

        # Set Orion URL (from source URL or config)
        orion_url = source_url or config.get("orion_url") or DEFAULT_ORION_URL
        config["orion_url"] = orion_url.rstrip("/")

        # Set API version (v2 or ngsi-ld/v1)
        config["api_version"] = config.get("api_version", DEFAULT_API_VERSION)

        # Entity filtering
        config["entity_types"] = config.get("entity_types", [])  # Filter by entity types
        config["entity_id_pattern"] = config.get("entity_id_pattern")  # Regex pattern for entity IDs
        config["entity_limit"] = int(config.get("entity_limit", DEFAULT_ENTITY_LIMIT))

        # Query options
        config["query"] = config.get("query")  # NGSI query expression
        config["georel"] = config.get("georel")  # Geo-location query
        config["geometry"] = config.get("geometry")  # Geometry type
        config["coords"] = config.get("coords")  # Coordinates

        # Authentication
        config["fiware_service"] = config.get("fiware_service")  # Multi-tenancy header
        config["fiware_servicepath"] = config.get("fiware_servicepath", "/")  # Service path
        config["auth_token"] = config.get("auth_token")  # Authentication token

        # Options
        config["include_attrs"] = config.get("include_attrs", [])  # Specific attributes to include
        config["exclude_attrs"] = config.get("exclude_attrs", [])  # Attributes to exclude

        return config

    def _get_http_session(self, config: Dict[str, Any]) -> Session:
        """Create HTTP session with appropriate headers."""
        session = requests.Session()
        headers = {
            "Accept": "application/json",
            "User-Agent": "ckanext-fiware-orion/0.1.0",
        }

        # Add FIWARE service headers if configured
        if config.get("fiware_service"):
            headers["Fiware-Service"] = config["fiware_service"]
        if config.get("fiware_servicepath"):
            headers["Fiware-ServicePath"] = config["fiware_servicepath"]

        # Add authentication token if configured
        if config.get("auth_token"):
            headers["X-Auth-Token"] = config["auth_token"]

        # For NGSI-LD, use different accept type
        if config.get("api_version") == "ngsi-ld/v1":
            headers["Accept"] = "application/ld+json"

        session.headers.update(headers)
        return session

    def _fetch_entities(
        self,
        session: Session,
        config: Dict[str, Any],
        offset: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fetch entities from Orion Context Broker."""
        api_version = config.get("api_version", DEFAULT_API_VERSION)

        if api_version == "ngsi-ld/v1":
            endpoint = f"{config['orion_url']}/ngsi-ld/v1/entities"
        else:
            endpoint = f"{config['orion_url']}/v2/entities"

        params: Dict[str, Any] = {
            "offset": offset,
            "limit": limit,
            "options": "keyValues",  # Simplified representation
        }

        # Add entity type filter
        if config.get("entity_types"):
            params["type"] = ",".join(config["entity_types"])

        # Add entity ID pattern
        if config.get("entity_id_pattern"):
            params["idPattern"] = config["entity_id_pattern"]

        # Add query filter
        if config.get("query"):
            params["q"] = config["query"]

        # Add geo-location query
        if config.get("georel"):
            params["georel"] = config["georel"]
            params["geometry"] = config.get("geometry", "point")
            params["coords"] = config.get("coords")

        # Add attribute filters
        if config.get("include_attrs"):
            params["attrs"] = ",".join(config["include_attrs"])

        log.debug("Fetching entities from %s with params: %s", endpoint, params)

        try:
            response: Response = session.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            entities = response.json()
            return entities if isinstance(entities, list) else []
        except RequestException as err:
            raise RuntimeError(f"HTTP request failed: {err}") from err
        except ValueError as err:
            raise RuntimeError(f"Response was not valid JSON: {err}") from err

    def _fetch_entity_by_id(
        self,
        session: Session,
        config: Dict[str, Any],
        entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch a specific entity by ID."""
        api_version = config.get("api_version", DEFAULT_API_VERSION)

        if api_version == "ngsi-ld/v1":
            endpoint = f"{config['orion_url']}/ngsi-ld/v1/entities/{entity_id}"
        else:
            endpoint = f"{config['orion_url']}/v2/entities/{entity_id}"

        params = {"options": "keyValues"}

        # Add attribute filters
        if config.get("include_attrs"):
            params["attrs"] = ",".join(config["include_attrs"])

        log.debug("Fetching entity from %s", endpoint)

        try:
            response: Response = session.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except RequestException as err:
            raise RuntimeError(f"HTTP request failed: {err}") from err
        except ValueError as err:
            raise RuntimeError(f"Response was not valid JSON: {err}") from err

    def _entity_to_package(
        self,
        entity: Dict[str, Any],
        harvest_object: HarvestObject,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert NGSI entity to CKAN package dictionary."""
        entity_id = entity.get("id", harvest_object.guid)
        entity_type = entity.get("type", "Unknown")

        # Generate title and description
        title = entity.get("name") or entity.get("title") or f"{entity_type}: {entity_id}"
        description = entity.get("description") or f"Context entity of type {entity_type} from FIWARE Orion"

        # Create package dictionary
        package_dict: Dict[str, Any] = {
            "id": entity_id,
            "title": title,
            "notes": description,
            "tags": self._extract_tags(entity, entity_type),
            "extras": self._make_extras(entity, config),
            "resources": self._make_resources(entity, config),
        }

        # Set owner organization from config or harvest source
        owner_org = config.get("owner_org")
        if not owner_org:
            # Get from harvest source publisher_id or job.source package
            if harvest_object.source.publisher_id:
                owner_org = harvest_object.source.publisher_id
            elif harvest_object.job and harvest_object.job.source:
                # Try to get from the source package
                try:
                    from ckan.logic import get_action
                    from ckan import model
                    context = {'model': model, 'ignore_auth': True}
                    source_pkg = get_action('package_show')(context, {'id': harvest_object.source.id})
                    owner_org = source_pkg.get('owner_org')
                except:
                    pass

        if owner_org:
            package_dict["owner_org"] = owner_org

        return package_dict

    def _extract_tags(self, entity: Dict[str, Any], entity_type: str) -> List[Dict[str, str]]:
        """Extract tags from entity."""
        tags: List[Dict[str, str]] = []

        # Add entity type as a tag
        tags.append({"name": entity_type.lower().replace(" ", "-")})

        # Add "fiware" and "ngsi" tags
        tags.append({"name": "fiware"})
        tags.append({"name": "ngsi"})

        # Add category if present
        if entity.get("category"):
            category = entity["category"]
            if isinstance(category, list):
                for cat in category:
                    tags.append({"name": str(cat).lower().replace(" ", "-")})
            else:
                tags.append({"name": str(category).lower().replace(" ", "-")})

        return tags

    def _make_extras(self, entity: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create extras from entity attributes."""
        extras: List[Dict[str, Any]] = []

        # Store entity type
        extras.append({"key": "entity_type", "value": entity.get("type")})

        # Store Orion URL
        extras.append({"key": "orion_url", "value": config.get("orion_url")})

        # Store all entity attributes as extras (excluding standard fields)
        exclude_fields = {"id", "type", "name", "title", "description", "category", "location"}
        exclude_attrs = set(config.get("exclude_attrs", []))

        for key, value in entity.items():
            if key not in exclude_fields and key not in exclude_attrs:
                # Convert value to string for CKAN extras
                if isinstance(value, (dict, list)):
                    extras.append({"key": key, "value": json.dumps(value)})
                else:
                    extras.append({"key": key, "value": str(value)})

        return extras

    def _make_resources(self, entity: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create resources from entity."""
        resources: List[Dict[str, Any]] = []

        # Create a JSON resource with the full entity data
        entity_id = entity.get("id")
        api_version = config.get("api_version", DEFAULT_API_VERSION)

        if api_version == "ngsi-ld/v1":
            entity_url = f"{config['orion_url']}/ngsi-ld/v1/entities/{entity_id}"
        else:
            entity_url = f"{config['orion_url']}/v2/entities/{entity_id}"

        resources.append({
            "name": f"NGSI Entity: {entity_id}",
            "description": "Full NGSI entity data from Orion Context Broker",
            "url": entity_url,
            "format": "JSON",
            "mime_type": "application/json",
        })

        # If entity has a location, add it as a GeoJSON resource
        if entity.get("location"):
            location = entity["location"]
            if isinstance(location, dict):
                resources.append({
                    "name": f"Location: {entity_id}",
                    "description": "Geographic location of the entity",
                    "url": entity_url + "?attrs=location",
                    "format": "GeoJSON",
                    "mime_type": "application/geo+json",
                })

        return resources
