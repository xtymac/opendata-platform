'use client'

import React, { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

interface MapViewProps {
  data: any[]
}

const MapViewComponent = ({ data }: MapViewProps) => {
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const L = require('leaflet')

      delete (L as any).Icon.Default.prototype._getIconUrl

      L.Icon.Default.mergeOptions({
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      })
    }
  }, [])

  const locations = data.filter(row => row.lat && row.lon && !isNaN(row.lat) && !isNaN(row.lon))

  if (locations.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        No location data available (requires lat/lon columns)
      </div>
    )
  }

  const centerLat = locations.reduce((sum, loc) => sum + parseFloat(loc.lat), 0) / locations.length
  const centerLon = locations.reduce((sum, loc) => sum + parseFloat(loc.lon), 0) / locations.length

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="h-96">
        <MapContainer
          center={[centerLat, centerLon]}
          zoom={10}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={true}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          />
          {locations.map((location, idx) => (
            <Marker key={idx} position={[parseFloat(location.lat), parseFloat(location.lon)]}>
              <Popup>
                <div className="text-sm">
                  {Object.entries(location).map(([key, value]) => (
                    <div key={key}>
                      <strong>{key}:</strong> {String(value)}
                    </div>
                  ))}
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  )
}

export default MapViewComponent