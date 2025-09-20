'use client'

import React, { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix for default marker icons in Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png'
})

interface MapData {
  name: string
  lat: number
  lon: number
  population: number
  address?: string
}

interface SimpleMapProps {
  data: MapData[]
}

export default function SimpleMap({ data }: SimpleMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const markersRef = useRef<L.Marker[]>([])

  useEffect(() => {
    if (!mapContainerRef.current) return

    // Clean up existing map
    if (mapRef.current) {
      mapRef.current.remove()
      mapRef.current = null
    }

    // Filter valid locations
    const validLocations = data.filter(d =>
      d.lat && d.lon && !isNaN(d.lat) && !isNaN(d.lon)
    )

    if (validLocations.length === 0) return

    // Calculate center
    const centerLat = validLocations.reduce((sum, loc) => sum + loc.lat, 0) / validLocations.length
    const centerLon = validLocations.reduce((sum, loc) => sum + loc.lon, 0) / validLocations.length

    // Create map
    const map = L.map(mapContainerRef.current).setView([centerLat, centerLon], 11)
    mapRef.current = map

    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(map)

    // Clear old markers
    markersRef.current.forEach(marker => marker.remove())
    markersRef.current = []

    // Add markers for each location
    validLocations.forEach(location => {
      const marker = L.marker([location.lat, location.lon]).addTo(map)

      const popupContent = `
        <div style="min-width: 200px;">
          <strong style="font-size: 16px;">${location.name}</strong><br/>
          ${location.address ? `<span>📍 ${location.address}</span><br/>` : ''}
          <span>👥 Population: ${location.population.toLocaleString()}</span><br/>
          <small style="color: #666;">
            Coordinates: ${location.lat.toFixed(4)}, ${location.lon.toFixed(4)}
          </small>
        </div>
      `
      marker.bindPopup(popupContent)
      markersRef.current.push(marker)
    })

    // Cleanup on unmount
    return () => {
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }
    }
  }, [data])

  if (!data || data.length === 0) {
    return (
      <div className="h-96 bg-gray-100 rounded flex items-center justify-center text-gray-500">
        No location data available
      </div>
    )
  }

  return (
    <div className="relative">
      <div
        ref={mapContainerRef}
        className="h-96 w-full rounded-lg z-0"
        style={{ position: 'relative' }}
      />
    </div>
  )
}