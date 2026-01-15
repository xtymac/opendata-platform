# FIWARE Orion Integration Setup Guide

This guide will help you set up and test the FIWARE Orion Context Broker integration with CKAN.

## Quick Start

### 1. Install the Extension

```bash
cd /home/ubuntu/ckan-stack

# Start the services (including new Orion and MongoDB)
docker-compose up -d

# Wait for services to be ready
docker-compose ps

# Install the FIWARE Orion harvester extension
docker exec ckan pip install -e /srv/app/src/ckanext-fiware-orion

# Restart CKAN to load the plugin
docker-compose restart ckan
```

### 2. Verify Installation

```bash
# Check CKAN logs for successful plugin loading
docker logs ckan | grep fiware_orion

# Verify Orion is running
curl http://localhost:1026/version

# Expected output: JSON with Orion version info
```

### 3. Create Sample NGSI Entities

Run the test script to populate Orion with sample smart city data:

```bash
bash /home/ubuntu/populate_orion_sample_data.sh
```

This will create:
- Smart Building entities with temperature/humidity sensors
- Air Quality Observation stations
- Weather stations
- Points of Interest

### 4. Create a Harvest Source

**Option A: Via Web Interface**

1. Navigate to: http://localhost/harvest (or https://opendata.uixai.org/harvest)
2. Click "Add Harvest Source"
3. Fill in:
   - **Title**: FIWARE Smart City Data
   - **URL**: `http://orion:1026`
   - **Source Type**: Select "FIWARE Orion Context Broker"
   - **Update Frequency**: MANUAL
   - **Configuration**:
     ```json
     {
       "api_version": "v2",
       "entity_types": ["Building", "AirQualityObserved", "WeatherObserved"],
       "entity_limit": 50
     }
     ```
4. Click "Save"

**Option B: Via Command Line**

```bash
docker exec ckan ckan -c /srv/app/ckan.ini harvester source create \
  fiware-smart-city \
  "FIWARE Smart City Data" \
  fiware_orion \
  http://orion:1026 \
  true \
  "" \
  "" \
  '{"api_version": "v2", "entity_types": ["Building", "AirQualityObserved"]}'
```

### 5. Run the Harvest

```bash
# Get the source ID
SOURCE_ID=$(docker exec ckan ckan -c /srv/app/ckan.ini harvester sources | grep fiware-smart-city | awk '{print $2}')

# Create and run a harvest job
docker exec ckan ckan -c /srv/app/ckan.ini harvester run $SOURCE_ID

# Monitor the harvest job
docker exec ckan ckan -c /srv/app/ckan.ini harvester job-all

# Check harvest logs
docker logs ckan | grep -i "fiware\|orion"
```

### 6. View Harvested Datasets

1. Navigate to: http://localhost/dataset (or https://opendata.uixai.org/dataset)
2. Look for datasets with "Building", "AirQualityObserved", etc.
3. Check that entity attributes are stored as dataset extras

## Advanced Configuration

### Filtering by Geographic Location

Harvest only entities near a specific location:

```json
{
  "api_version": "v2",
  "entity_types": ["PointOfInterest"],
  "georel": "near;maxDistance:5000",
  "geometry": "point",
  "coords": "40.418889,-3.691944"
}
```

### Using NGSI-LD

For NGSI-LD format (recommended for new deployments):

```json
{
  "api_version": "ngsi-ld/v1",
  "entity_types": ["Building"],
  "entity_limit": 100
}
```

### Multi-tenancy Support

If your Orion instance uses FIWARE-Service headers:

```json
{
  "api_version": "v2",
  "fiware_service": "smartcity",
  "fiware_servicepath": "/environment",
  "entity_types": ["Sensor"]
}
```

### Filtering Attributes

Only include specific attributes:

```json
{
  "api_version": "v2",
  "include_attrs": ["temperature", "humidity", "location"],
  "entity_types": ["Sensor"]
}
```

## Troubleshooting

### Extension not loading

```bash
# Check if extension is installed
docker exec ckan pip list | grep fiware

# Reinstall if needed
docker exec ckan pip install -e /srv/app/src/ckanext-fiware-orion
docker-compose restart ckan
```

### Harvester not appearing in dropdown

1. Verify plugin is in CKAN__PLUGINS environment variable:
   ```bash
   docker exec ckan env | grep CKAN__PLUGINS
   ```
2. Should include: `fiware_orion_harvester`
3. If not, update docker-compose.yml and restart

### No entities found

```bash
# Check Orion has entities
curl http://localhost:1026/v2/entities

# Test from within CKAN container
docker exec ckan curl http://orion:1026/v2/entities

# Check connectivity
docker exec ckan ping -c 3 orion
```

### Harvest job fails

```bash
# View detailed error messages
docker exec ckan ckan -c /srv/app/ckan.ini harvester job-show <job-id>

# Check CKAN logs
docker logs ckan --tail 100 | grep -i error

# Check Orion logs
docker logs fiware-orion --tail 50
```

## Testing with Real FIWARE Data

You can connect to public FIWARE instances for testing:

### FIWARE Tour Guide

```json
{
  "orion_url": "http://tourguide.lab.fiware.org:1026",
  "api_version": "v2",
  "entity_types": ["Restaurant", "Point"],
  "entity_limit": 20
}
```

**Note**: Public instances may require authentication or have rate limits.

## Architecture Overview

```
┌─────────────────┐         ┌──────────────────┐
│  FIWARE Orion   │         │   MongoDB        │
│ Context Broker  │────────▶│  (Persistence)   │
│   Port: 1026    │         │                  │
└────────┬────────┘         └──────────────────┘
         │
         │ NGSI v2/LD API
         │
         ▼
┌─────────────────────────────────────────────┐
│         CKAN Harvester Framework            │
│  ┌──────────────────────────────────────┐   │
│  │  ckanext-fiware-orion                │   │
│  │  ┌──────┐  ┌──────┐  ┌────────┐     │   │
│  │  │Gather├─▶│Fetch ├─▶│ Import │     │   │
│  │  └──────┘  └──────┘  └────────┘     │   │
│  │                                      │   │
│  │  NGSI Entity → CKAN Dataset          │   │
│  └──────────────────────────────────────┘   │
│                                             │
│            PostgreSQL + Solr                │
└─────────────────────────────────────────────┘
```

## Next Steps

1. **Set up scheduled harvesting**: Configure cron job for automatic updates
2. **Create custom entity mappings**: Modify harvester.py for domain-specific needs
3. **Add NGSI subscriptions**: Implement real-time updates (advanced)
4. **Integrate with FIWARE ecosystem**: Connect to other FIWARE Generic Enablers

## Resources

- [FIWARE Orion Documentation](https://fiware-orion.readthedocs.io/)
- [NGSI v2 Specification](http://fiware.github.io/specifications/ngsiv2/stable/)
- [NGSI-LD Specification](https://www.etsi.org/deliver/etsi_gs/CIM/001_099/009/01.07.01_60/gs_CIM009v010701p.pdf)
- [CKAN Harvesting Guide](https://docs.ckan.org/en/latest/maintaining/harvesting.html)
- [ckanext-fiware-orion README](ckan-stack/extensions/ckanext-fiware-orion/README.md)
