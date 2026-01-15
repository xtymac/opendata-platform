#!/bin/bash

# Script to populate FIWARE Orion with sample smart city data
# This creates test entities for CKAN harvesting

set -e

ORION_URL="http://localhost:1026"

echo "================================================"
echo " Populating FIWARE Orion with Sample Data"
echo "================================================"
echo ""

# Check if Orion is accessible
echo "[1/5] Checking Orion Context Broker..."
if curl -s -f "${ORION_URL}/version" > /dev/null; then
    echo "✓ Orion is accessible at ${ORION_URL}"
else
    echo "✗ Error: Cannot connect to Orion at ${ORION_URL}"
    echo "  Make sure Orion is running: docker-compose up -d orion"
    exit 1
fi

echo ""
echo "[2/5] Creating Smart Building entities..."

# Building 1 - FIWARE Office
curl -s -X POST "${ORION_URL}/v2/entities?options=keyValues" \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "urn:ngsi-ld:Building:fiware-office-001",
    "type": "Building",
    "name": "FIWARE Smart Office Building",
    "description": "Main office building with IoT environmental sensors",
    "address": "Calle de la Tecnología 42, Madrid",
    "category": ["office", "commercial"],
    "temperature": 22.5,
    "humidity": 45,
    "occupancy": 120,
    "energyConsumption": 450.5,
    "location": {
      "type": "Point",
      "coordinates": [-3.7167, 40.4167]
    }
  }' && echo "✓ Created FIWARE Office Building"

# Building 2 - Smart Home
curl -s -X POST "${ORION_URL}/v2/entities?options=keyValues" \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "urn:ngsi-ld:Building:smart-home-001",
    "type": "Building",
    "name": "Smart Home Demonstration",
    "description": "Residential smart home with automation systems",
    "address": "Avenida de la Innovación 15, Barcelona",
    "category": ["residential"],
    "temperature": 21.0,
    "humidity": 50,
    "occupancy": 4,
    "energyConsumption": 85.3,
    "location": {
      "type": "Point",
      "coordinates": [2.1686, 41.3874]
    }
  }' && echo "✓ Created Smart Home"

# Building 3 - Data Center
curl -s -X POST "${ORION_URL}/v2/entities?options=keyValues" \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "urn:ngsi-ld:Building:datacenter-001",
    "type": "Building",
    "name": "Cloud Data Center",
    "description": "High-tech data center with environmental monitoring",
    "address": "Polígono Industrial Tech Park, Valencia",
    "category": ["datacenter", "industrial"],
    "temperature": 18.5,
    "humidity": 40,
    "occupancy": 25,
    "energyConsumption": 1250.0,
    "location": {
      "type": "Point",
      "coordinates": [-0.3763, 39.4699]
    }
  }' && echo "✓ Created Data Center"

echo ""
echo "[3/5] Creating Air Quality Observation stations..."

# Air Quality Station 1
curl -s -X POST "${ORION_URL}/v2/entities?options=keyValues" \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "urn:ngsi-ld:AirQualityObserved:madrid-centro-001",
    "type": "AirQualityObserved",
    "name": "Madrid Centro Air Quality Station",
    "description": "Air quality monitoring station in city center",
    "address": "Plaza Mayor, Madrid",
    "dateObserved": "2025-11-18T10:00:00Z",
    "NO2": 42.5,
    "CO": 0.8,
    "PM10": 25.3,
    "PM25": 15.7,
    "O3": 55.2,
    "temperature": 15.5,
    "relativeHumidity": 65,
    "airQualityIndex": 75,
    "location": {
      "type": "Point",
      "coordinates": [-3.7037, 40.4168]
    }
  }' && echo "✓ Created Madrid Air Quality Station"

# Air Quality Station 2
curl -s -X POST "${ORION_URL}/v2/entities?options=keyValues" \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "urn:ngsi-ld:AirQualityObserved:barcelona-port-001",
    "type": "AirQualityObserved",
    "name": "Barcelona Port Air Quality Station",
    "description": "Air quality monitoring near harbor area",
    "address": "Port Vell, Barcelona",
    "dateObserved": "2025-11-18T10:00:00Z",
    "NO2": 38.2,
    "CO": 0.6,
    "PM10": 22.8,
    "PM25": 13.5,
    "O3": 62.1,
    "temperature": 17.2,
    "relativeHumidity": 72,
    "airQualityIndex": 68,
    "location": {
      "type": "Point",
      "coordinates": [2.1851, 41.3764]
    }
  }' && echo "✓ Created Barcelona Air Quality Station"

echo ""
echo "[4/5] Creating Weather Observation stations..."

# Weather Station 1
curl -s -X POST "${ORION_URL}/v2/entities?options=keyValues" \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "urn:ngsi-ld:WeatherObserved:madrid-weather-001",
    "type": "WeatherObserved",
    "name": "Madrid Weather Station",
    "description": "Meteorological observation station",
    "address": "Retiro Park, Madrid",
    "dateObserved": "2025-11-18T10:00:00Z",
    "temperature": 16.5,
    "relativeHumidity": 62,
    "atmosphericPressure": 1013.2,
    "windSpeed": 12.5,
    "windDirection": 180,
    "precipitation": 0,
    "weatherType": "sunny",
    "location": {
      "type": "Point",
      "coordinates": [-3.6833, 40.4153]
    }
  }' && echo "✓ Created Madrid Weather Station"

# Weather Station 2
curl -s -X POST "${ORION_URL}/v2/entities?options=keyValues" \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "urn:ngsi-ld:WeatherObserved:valencia-weather-001",
    "type": "WeatherObserved",
    "name": "Valencia Weather Station",
    "description": "Coastal meteorological station",
    "address": "Malvarrosa Beach, Valencia",
    "dateObserved": "2025-11-18T10:00:00Z",
    "temperature": 18.8,
    "relativeHumidity": 70,
    "atmosphericPressure": 1015.5,
    "windSpeed": 18.3,
    "windDirection": 90,
    "precipitation": 0,
    "weatherType": "partlyCloudy",
    "location": {
      "type": "Point",
      "coordinates": [-0.3231, 39.4817]
    }
  }' && echo "✓ Created Valencia Weather Station"

echo ""
echo "[5/5] Creating Points of Interest..."

# POI 1
curl -s -X POST "${ORION_URL}/v2/entities?options=keyValues" \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "urn:ngsi-ld:PointOfInterest:museum-prado",
    "type": "PointOfInterest",
    "name": "Museo del Prado",
    "description": "One of the world'\''s premier art museums",
    "category": ["museum", "culture", "tourism"],
    "address": "Calle de Ruiz de Alarcón 23, Madrid",
    "openingHours": "10:00-20:00",
    "capacity": 3000,
    "currentOccupancy": 450,
    "website": "https://www.museodelprado.es",
    "location": {
      "type": "Point",
      "coordinates": [-3.6922, 40.4138]
    }
  }' && echo "✓ Created Museo del Prado POI"

# POI 2
curl -s -X POST "${ORION_URL}/v2/entities?options=keyValues" \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "urn:ngsi-ld:PointOfInterest:sagrada-familia",
    "type": "PointOfInterest",
    "name": "Sagrada Família",
    "description": "Iconic basilica designed by Antoni Gaudí",
    "category": ["monument", "architecture", "tourism"],
    "address": "Carrer de Mallorca 401, Barcelona",
    "openingHours": "09:00-20:00",
    "capacity": 5000,
    "currentOccupancy": 2100,
    "website": "https://sagradafamilia.org",
    "location": {
      "type": "Point",
      "coordinates": [2.1744, 41.4036]
    }
  }' && echo "✓ Created Sagrada Família POI"

echo ""
echo "================================================"
echo " Sample Data Population Complete!"
echo "================================================"
echo ""
echo "Summary:"
curl -s "${ORION_URL}/v2/entities" | python3 -m json.tool | grep -E '"id"|"type"' | head -20

echo ""
echo "Entity counts by type:"
echo "  - Buildings: $(curl -s "${ORION_URL}/v2/entities?type=Building" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")"
echo "  - Air Quality Stations: $(curl -s "${ORION_URL}/v2/entities?type=AirQualityObserved" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")"
echo "  - Weather Stations: $(curl -s "${ORION_URL}/v2/entities?type=WeatherObserved" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")"
echo "  - Points of Interest: $(curl -s "${ORION_URL}/v2/entities?type=PointOfInterest" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")"
echo ""
echo "Next step: Create a harvest source in CKAN to import these entities!"
echo "See FIWARE_ORION_SETUP.md for instructions."
