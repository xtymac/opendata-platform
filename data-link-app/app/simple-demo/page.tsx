'use client'

import React, { useState } from 'react'
import Papa from 'papaparse'
import dynamic from 'next/dynamic'
import { Upload, MapPin, Users, Search, Map as MapIcon } from 'lucide-react'

const MapView = dynamic(() => import('../components/SimpleMap'), {
  ssr: false,
  loading: () => <div className="h-96 bg-gray-100 animate-pulse rounded"></div>
})

interface AEDData {
  id: string
  name: string
  lat: number
  lon: number
  city_code: string
  address?: string
}

interface PopulationData {
  city_code: string
  population: number
}

interface JoinedData extends AEDData {
  population: number
}

export default function SimpleDemo() {
  const [aedData, setAedData] = useState<AEDData[]>([])
  const [populationData, setPopulationData] = useState<PopulationData[]>([])
  const [results, setResults] = useState<JoinedData[]>([])
  const [showResults, setShowResults] = useState(false)
  const [showMap, setShowMap] = useState(true)

  const normalizeColumnName = (col: string): string => {
    const mappings: Record<string, string> = {
      '市区町村コード': 'city_code',
      '名称': 'name',
      '名前': 'name',
      '施設名': 'name',
      '緯度': 'lat',
      '経度': 'lon',
      'longitude': 'lon',
      'latitude': 'lat',
      '人口': 'population',
      '住所': 'address',
      'id': 'id',
      'ID': 'id'
    }
    return mappings[col] || col.toLowerCase().replace(/\s+/g, '_')
  }

  const handleAEDUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    console.log('Parsing AED file:', file.name)

    Papa.parse(file, {
      header: true,
      complete: (results) => {
        console.log('AED parse complete, rows:', results.data.length)
        const normalized = results.data.map((row: any) => {
          const newRow: any = {}
          Object.keys(row).forEach(key => {
            const normalizedKey = normalizeColumnName(key)
            newRow[normalizedKey] = row[key]
          })
          return {
            id: newRow.id || Math.random().toString(),
            name: newRow.name || 'Unknown AED',
            lat: parseFloat(newRow.lat) || 0,
            lon: parseFloat(newRow.lon) || 0,
            city_code: String(newRow.city_code || ''),
            address: newRow.address || ''
          }
        }).filter((row: AEDData) => row.city_code)

        console.log('Setting AED data:', normalized.length, 'rows')
        setAedData(normalized as AEDData[])
      },
      error: (error: any) => {
        console.error('Error parsing AED file:', error)
      }
    })
  }

  const handlePopulationUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    console.log('Parsing Population file:', file.name)

    Papa.parse(file, {
      header: true,
      complete: (results) => {
        console.log('Population parse complete, rows:', results.data.length)
        const normalized = results.data.map((row: any) => {
          const newRow: any = {}
          Object.keys(row).forEach(key => {
            const normalizedKey = normalizeColumnName(key)
            newRow[normalizedKey] = row[key]
          })
          return {
            city_code: String(newRow.city_code || ''),
            population: parseInt(newRow.population) || 0
          }
        }).filter((row: PopulationData) => row.city_code)

        console.log('Setting population data:', normalized.length, 'rows')
        setPopulationData(normalized as PopulationData[])
      },
      error: (error: any) => {
        console.error('Error parsing population file:', error)
      }
    })
  }

  const findAEDsWithPopulation = () => {
    // Create population lookup map
    const populationMap = new Map<string, number>()
    populationData.forEach(p => {
      populationMap.set(p.city_code, p.population)
    })

    // Perform left join and filter
    const joined = aedData
      .map(aed => ({
        ...aed,
        population: populationMap.get(aed.city_code) || 0
      }))
      .filter(aed => aed.population > 1000)

    setResults(joined)
    setShowResults(true)
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">AED Population Coverage Demo</h1>

        {/* Upload Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              AED Locations Data
            </h3>
            <label className="block">
              <div className={`border-2 border-dashed rounded p-4 text-center cursor-pointer transition ${
                aedData.length > 0 ? 'border-green-400 bg-green-50' : 'border-gray-300 hover:border-blue-400'
              }`}>
                <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                <p className="text-sm text-gray-600">
                  {aedData.length > 0
                    ? `✓ Loaded ${aedData.length} AED locations`
                    : 'Upload AED CSV (id, name, lat, lon, city_code)'}
                </p>
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleAEDUpload}
                  className="hidden"
                />
              </div>
            </label>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <Users className="w-4 h-4" />
              Population Data
            </h3>
            <label className="block">
              <div className={`border-2 border-dashed rounded p-4 text-center cursor-pointer transition ${
                populationData.length > 0 ? 'border-green-400 bg-green-50' : 'border-gray-300 hover:border-blue-400'
              }`}>
                <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                <p className="text-sm text-gray-600">
                  {populationData.length > 0
                    ? `✓ Loaded ${populationData.length} city populations`
                    : 'Upload Population CSV (city_code, population)'}
                </p>
                <input
                  type="file"
                  accept=".csv"
                  onChange={handlePopulationUpload}
                  className="hidden"
                />
              </div>
            </label>
          </div>
        </div>

        {/* Action Button */}
        <div className="text-center mb-6">
          <button
            onClick={findAEDsWithPopulation}
            disabled={aedData.length === 0 || populationData.length === 0}
            className={`px-6 py-3 rounded-lg font-semibold flex items-center gap-2 mx-auto transition ${
              aedData.length > 0 && populationData.length > 0
                ? 'bg-blue-500 text-white hover:bg-blue-600'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            <Search className="w-5 h-5" />
            Find AEDs with population coverage &gt; 1000
          </button>
        </div>

        {/* Results Section */}
        {showResults && (
          <div className="space-y-4">
            <div className="bg-white rounded-lg shadow p-4">
              <div className="flex justify-between items-center mb-3">
                <h3 className="font-semibold">
                  Results: {results.length} AEDs in areas with population &gt; 1000
                </h3>
                {results.length > 0 && (
                  <button
                    onClick={() => setShowMap(!showMap)}
                    className="text-sm bg-blue-500 text-white px-3 py-1 rounded hover:bg-blue-600 flex items-center gap-1"
                  >
                    <MapIcon className="w-4 h-4" />
                    {showMap ? 'Hide Map' : 'Show Map'}
                  </button>
                )}
              </div>

              {results.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left">AED Name</th>
                        <th className="px-4 py-2 text-left">Address</th>
                        <th className="px-4 py-2 text-left">Lat</th>
                        <th className="px-4 py-2 text-left">Lon</th>
                        <th className="px-4 py-2 text-left">Population</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {results.map((row, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="px-4 py-2">{row.name}</td>
                          <td className="px-4 py-2">{row.address || '-'}</td>
                          <td className="px-4 py-2">{row.lat.toFixed(6)}</td>
                          <td className="px-4 py-2">{row.lon.toFixed(6)}</td>
                          <td className="px-4 py-2">{row.population.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-gray-500 text-center py-4">
                  No AEDs found in areas with population &gt; 1000
                </p>
              )}
            </div>

            {/* Map View */}
            {showMap && results.length > 0 && results.some(r => r.lat && r.lon) && (
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="font-semibold mb-3">Map View</h3>
                <MapView data={results} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}