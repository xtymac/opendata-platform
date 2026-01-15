# FIWARE-Orion + CKAN - Quick Start Guide

## ✅ What's Running

### Services Status
- ✅ **CKAN**: http://localhost (or https://opendata.uixai.org)
- ✅ **FIWARE Orion**: http://localhost:1026
- ✅ **MongoDB**: Running (backend for Orion)
- ✅ **ckanext-fiware-orion**: Installed and loaded

### Sample Data
- ✅ 8 NGSI entities loaded in Orion Context Broker
  - 3 Buildings
  - 2 Air Quality Stations
  - 2 Weather Stations
  - 1 Point of Interest

---

## 🚀 Next Step: Create Your First Harvest

### Option 1: Via Web Interface (Recommended)

1. **Access Harvest Admin** (requires login):
   ```
   https://opendata.uixai.org/harvest
   ```

2. **Click "Add Harvest Source"**

3. **Fill in the form**:
   - **Title**: `FIWARE Smart City Data`
   - **URL**: `http://orion:1026`
   - **Source Type**: Select **"FIWARE Orion Context Broker"**
   - **Update Frequency**: `MANUAL` (or choose a schedule)
   - **Configuration**:
     ```json
     {
       "api_version": "v2",
       "entity_types": ["Building", "AirQualityObserved", "WeatherObserved"],
       "entity_limit": 50
     }
     ```

4. **Save** and click **"Reharvest"**

5. **Monitor Progress**:
   - Click "Admin" → "Harvest Sources"
   - Click on your source to see job status
   - Wait for job to complete

6. **View Results**:
   - Navigate to https://opendata.uixai.org/dataset
   - You should see 8 new datasets from Orion entities!

---

### Option 2: Via Command Line

```bash
# 1. Create harvest source
docker exec ckan ckan -c /srv/app/ckan.ini harvester source create \
  fiware-smart-city \
  "FIWARE Smart City Data" \
  fiware_orion \
  http://orion:1026 \
  true \
  "" \
  "" \
  '{"api_version": "v2", "entity_types": ["Building", "AirQualityObserved", "WeatherObserved"]}'

# 2. Run harvest job
docker exec ckan ckan -c /srv/app/ckan.ini harvester run

# 3. Check status
docker exec ckan ckan -c /srv/app/ckan.ini harvester jobs

# 4. View logs
docker logs ckan | grep -i "fiware\|harvest"
```

---

## 📊 Verify Integration

### Check Orion Entities
```bash
# List all entities
curl http://localhost:1026/v2/entities | python3 -m json.tool

# Get specific entity
curl http://localhost:1026/v2/entities/urn:ngsi-ld:Building:fiware-office-001 | python3 -m json.tool

# Count by type
curl "http://localhost:1026/v2/entities?type=Building" | python3 -m json.tool
```

### Check CKAN Datasets
```bash
# List datasets via API
curl http://localhost/api/3/action/package_list | python3 -m json.tool

# Search for FIWARE datasets
curl "http://localhost/api/3/action/package_search?q=tags:fiware" | python3 -m json.tool
```

---

## 🔧 Configuration Examples

### Filter by Geographic Location
```json
{
  "api_version": "v2",
  "entity_types": ["PointOfInterest"],
  "georel": "near;maxDistance:5000",
  "geometry": "point",
  "coords": "40.418889,-3.691944"
}
```

### Filter by Attributes
```json
{
  "api_version": "v2",
  "entity_types": ["Building"],
  "include_attrs": ["temperature", "humidity", "location"],
  "query": "temperature>20"
}
```

### NGSI-LD Format
```json
{
  "api_version": "ngsi-ld/v1",
  "entity_types": ["Building"],
  "entity_limit": 100
}
```

### Multi-tenancy
```json
{
  "api_version": "v2",
  "fiware_service": "smartcity",
  "fiware_servicepath": "/environment",
  "entity_types": ["Sensor"]
}
```

---

## 📁 Documentation Files

- [FIWARE_ORION_SETUP.md](FIWARE_ORION_SETUP.md) - Detailed setup guide
- [FIWARE_INTEGRATION_SUMMARY.md](FIWARE_INTEGRATION_SUMMARY.md) - Full implementation details
- [ckanext-fiware-orion README](ckan-stack/extensions/ckanext-fiware-orion/README.md) - Extension documentation

---

## 🛠️ Useful Commands

### Manage Orion Data
```bash
# Add a new entity
curl -X POST http://localhost:1026/v2/entities?options=keyValues \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "urn:ngsi-ld:Sensor:001",
    "type": "Sensor",
    "temperature": 22.5,
    "location": {"type": "Point", "coordinates": [-3.7, 40.4]}
  }'

# Update an entity
curl -X PATCH http://localhost:1026/v2/entities/urn:ngsi-ld:Sensor:001/attrs?options=keyValues \
  -H 'Content-Type: application/json' \
  -d '{"temperature": 23.0}'

# Delete an entity
curl -X DELETE http://localhost:1026/v2/entities/urn:ngsi-ld:Sensor:001
```

### Manage Harvest Jobs
```bash
# List all harvest sources
docker exec ckan ckan -c /srv/app/ckan.ini harvester sources

# Show specific source details
docker exec ckan ckan -c /srv/app/ckan.ini harvester source show <source-id>

# Rerun harvest for a source
docker exec ckan ckan -c /srv/app/ckan.ini harvester run <source-id>

# Clear previous harvest
docker exec ckan ckan -c /srv/app/ckan.ini harvester clearsource <source-id>
```

### Service Management
```bash
# Restart services
docker compose restart ckan
docker compose restart orion
docker compose restart mongo

# View logs
docker logs ckan --tail 100 -f
docker logs fiware-orion --tail 100 -f

# Check service health
docker ps | grep -E "ckan|orion|mongo"
curl http://localhost:1026/version
curl http://localhost/api/3/action/status_show
```

---

## 🔍 Troubleshooting

### Harvest job fails
```bash
# Check harvest job details
docker exec ckan ckan -c /srv/app/ckan.ini harvester job-show <job-id>

# View CKAN logs
docker logs ckan | grep -i error

# Verify Orion connectivity
docker exec ckan curl http://orion:1026/version
```

### No entities found
```bash
# Verify Orion has data
curl http://localhost:1026/v2/entities

# Repopulate sample data
bash /home/ubuntu/populate_orion_sample_data.sh
```

### Plugin not loading
```bash
# Verify plugin is installed
docker exec ckan pip list | grep fiware

# Check CKAN configuration
docker exec ckan env | grep CKAN__PLUGINS

# Reinstall if needed
docker exec ckan pip install -e /srv/app/src/ckanext-fiware-orion --force-reinstall
docker compose restart ckan
```

---

## 🎯 What You Can Do Now

1. ✅ **Harvest existing data** - Run your first harvest to import the 8 sample entities
2. ✅ **Add more entities to Orion** - Create custom IoT/sensor data
3. ✅ **Set up scheduled harvesting** - Configure automatic updates
4. ✅ **Customize mappings** - Edit harvester.py to match your data model
5. ✅ **Integrate with other FIWARE components** - Connect to IoT Agents, QuantumLeap, etc.

---

## 📚 Learn More

- **FIWARE Platform**: https://www.fiware.org/
- **Orion Context Broker**: https://fiware-orion.readthedocs.io/
- **NGSI v2 Spec**: http://fiware.github.io/specifications/ngsiv2/stable/
- **CKAN Harvesting**: https://docs.ckan.org/en/latest/maintaining/harvesting.html

---

**Ready to harvest?** Follow the steps above and start ingesting FIWARE context data into your CKAN portal! 🚀
