# ckanext-fiware-orion

FIWARE Orion Context Broker harvester extension for CKAN. This extension enables CKAN to harvest context data from FIWARE Orion Context Broker using both NGSI v2 and NGSI-LD APIs.

## Features

- **NGSI v2 Support**: Harvest entities from Orion Context Broker using NGSI v2 API
- **NGSI-LD Support**: Full support for NGSI-LD format with JSON-LD contexts
- **Entity Filtering**: Filter entities by type, ID pattern, attributes, and geo-location
- **Multi-tenancy**: Support for FIWARE-Service and FIWARE-ServicePath headers
- **Flexible Mapping**: Automatic conversion of NGSI entities to CKAN datasets
- **Authentication**: Support for token-based authentication

## Requirements

- CKAN 2.10+
- ckanext-harvest
- FIWARE Orion Context Broker (running and accessible)

## Installation

1. Install the extension:
```bash
cd /srv/app/src/ckanext-fiware-orion
pip install -e .
```

2. Add `fiware_orion_harvester` to the `ckan.plugins` setting in your CKAN configuration file:
```ini
ckan.plugins = ... harvest fiware_orion_harvester
```

3. Restart CKAN

## Configuration

### Creating a Harvest Source

1. Navigate to `/harvest` in your CKAN instance
2. Click "Add Harvest Source"
3. Fill in the form:
   - **URL**: Your Orion Context Broker URL (e.g., `http://orion:1026`)
   - **Source type**: Select "FIWARE Orion Context Broker"
   - **Configuration**: See below for configuration options

### Configuration Options

The harvester accepts a JSON configuration with the following options:

```json
{
  "api_version": "v2",
  "entity_types": ["Building", "Room"],
  "entity_id_pattern": "^urn:ngsi-ld:.*",
  "entity_limit": 100,
  "query": "temperature>20",
  "fiware_service": "openiot",
  "fiware_servicepath": "/environment",
  "auth_token": "your-auth-token",
  "include_attrs": ["temperature", "humidity"],
  "exclude_attrs": ["internal_id"],
  "owner_org": "my-organization"
}
```

#### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_version` | string | `"v2"` | API version: `"v2"` for NGSI v2 or `"ngsi-ld/v1"` for NGSI-LD |
| `entity_types` | array | `[]` | Filter entities by type (e.g., `["Building", "Room"]`) |
| `entity_id_pattern` | string | - | Regex pattern to filter entity IDs |
| `entity_limit` | integer | `100` | Number of entities to fetch per page |
| `query` | string | - | NGSI query expression (e.g., `"temperature>20"`) |
| `georel` | string | - | Geo-location relationship (e.g., `"near;maxDistance:1000"`) |
| `geometry` | string | - | Geometry type (e.g., `"point"`, `"polygon"`) |
| `coords` | string | - | Coordinates for geo-query |
| `fiware_service` | string | - | FIWARE-Service header for multi-tenancy |
| `fiware_servicepath` | string | `"/"` | FIWARE-ServicePath header |
| `auth_token` | string | - | Authentication token (X-Auth-Token header) |
| `include_attrs` | array | `[]` | Only include these attributes |
| `exclude_attrs` | array | `[]` | Exclude these attributes from extras |
| `owner_org` | string | - | CKAN organization to assign datasets to |

### Example Configurations

#### Basic NGSI v2 Harvesting

```json
{
  "api_version": "v2"
}
```

#### Filter by Entity Type

```json
{
  "api_version": "v2",
  "entity_types": ["AirQualityObserved", "WeatherObserved"]
}
```

#### NGSI-LD with Multi-tenancy

```json
{
  "api_version": "ngsi-ld/v1",
  "fiware_service": "smart-city",
  "fiware_servicepath": "/environment/sensors",
  "entity_types": ["Sensor"]
}
```

#### Geo-location Query

```json
{
  "api_version": "v2",
  "entity_types": ["PointOfInterest"],
  "georel": "near;maxDistance:1000",
  "geometry": "point",
  "coords": "40.418889,-3.691944"
}
```

## Entity to Dataset Mapping

The harvester automatically converts NGSI entities to CKAN datasets:

- **Entity ID** → Dataset ID
- **Entity Type** → Tag
- **name/title attribute** → Dataset title
- **description attribute** → Dataset description
- **All other attributes** → Dataset extras (as JSON)
- **location attribute** → GeoJSON resource

## Running a Harvest

### Via Web Interface

1. Go to `/harvest`
2. Find your harvest source
3. Click "Manage" → "Reharvest"

### Via Command Line

```bash
# Run a harvest job
ckan -c /etc/ckan/production.ini harvester run

# Run specific source
ckan -c /etc/ckan/production.ini harvester run <source-id>

# Gather, fetch, and import stages separately
ckan -c /etc/ckan/production.ini harvester gather_consumer
ckan -c /etc/ckan/production.ini harvester fetch_consumer
```

## Testing with Sample Data

You can test the harvester by creating sample entities in Orion:

```bash
# Create a sample Building entity
curl -X POST http://localhost:1026/v2/entities \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "urn:ngsi-ld:Building:001",
    "type": "Building",
    "name": "FIWARE Building",
    "description": "A smart building with IoT sensors",
    "address": "Plaza de España, Madrid",
    "temperature": 22.5,
    "humidity": 45,
    "location": {
      "type": "Point",
      "coordinates": [-3.7167, 40.4167]
    }
  }'
```

Then run the harvester to import this entity into CKAN.

## Troubleshooting

### Harvester not showing up

- Ensure `harvest` and `fiware_orion_harvester` are both in `ckan.plugins`
- Restart CKAN after adding the plugin
- Check CKAN logs for errors

### No entities harvested

- Verify Orion Context Broker is accessible from CKAN container
- Check Orion has entities: `curl http://orion:1026/v2/entities`
- Review harvest job errors in CKAN admin interface
- Check CKAN logs for detailed error messages

### Connection errors

- Ensure Orion service is running: `docker ps | grep orion`
- Verify network connectivity: `docker exec ckan curl http://orion:1026/version`
- Check firewall settings if Orion is on external server

## Architecture

The harvester follows CKAN's three-stage harvest pattern:

1. **Gather Stage**: Queries Orion for entity IDs, creates HarvestObject for each
2. **Fetch Stage**: Retrieves full entity data from Orion for each HarvestObject
3. **Import Stage**: Converts NGSI entities to CKAN datasets and creates/updates them

## License

AGPL v3

## Support

For issues and questions:
- Check CKAN logs: `/var/log/ckan/`
- Review Orion logs: `docker logs fiware-orion`
- FIWARE Orion documentation: https://fiware-orion.readthedocs.io/
