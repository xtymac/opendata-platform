'use client'

import React, { useState, useMemo } from 'react'
import dynamic from 'next/dynamic'
import FileUploader from './components/FileUploader'
import DataTable from './components/DataTable'
import FilterPanel from './components/FilterPanel'
import JoinPanel from './components/JoinPanel'
import { Dataset, FilterCondition, JoinConfig } from './types'
import { applyFilter, joinDatasets, findCommonColumns } from './lib/dataProcessing'
import { Database, Map, Table, FileUp } from 'lucide-react'

const MapView = dynamic(() => import('./components/MapView'), {
  ssr: false,
  loading: () => <div className="h-96 bg-gray-100 animate-pulse rounded-lg"></div>
})

export default function Home() {
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [activeDatasetId, setActiveDatasetId] = useState<string | null>(null)
  const [filters, setFilters] = useState<FilterCondition[]>([])
  const [viewMode, setViewMode] = useState<'table' | 'map'>('table')

  const handleDatasetLoad = (dataset: Dataset) => {
    setDatasets(prev => {
      const updated = [...prev, dataset]
      if (!activeDatasetId) {
        setActiveDatasetId(dataset.id)
      }
      return updated
    })
  }

  const handleJoin = (config: JoinConfig) => {
    const leftDataset = datasets.find(d => d.id === config.leftDataset)
    const rightDataset = datasets.find(d => d.id === config.rightDataset)

    if (leftDataset && rightDataset) {
      const joinedData = joinDatasets(config, leftDataset.data, rightDataset.data)
      const allColumns = Array.from(new Set([
        ...leftDataset.columns,
        ...rightDataset.columns
      ]))

      const joinedDataset: Dataset = {
        id: `joined-${Date.now()}`,
        name: `${leftDataset.name} + ${rightDataset.name}`,
        data: joinedData,
        columns: allColumns,
        originalColumns: allColumns
      }

      setDatasets(prev => [...prev, joinedDataset])
      setActiveDatasetId(joinedDataset.id)
    }
  }

  const activeDataset = datasets.find(d => d.id === activeDatasetId)

  const filteredData = useMemo(() => {
    if (!activeDataset) return []
    let data = [...activeDataset.data]

    filters.forEach(filter => {
      if (filter.value) {
        data = applyFilter(data, filter)
      }
    })

    return data
  }, [activeDataset, filters])

  const commonColumns = useMemo(() => {
    if (datasets.length <= 1) return activeDataset?.columns || []
    return findCommonColumns(datasets)
  }, [datasets, activeDataset])

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto p-4 max-w-7xl">
        <h1 className="text-3xl font-bold mb-6 text-gray-800">Data Link App</h1>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-6">
          <div className="lg:col-span-1 space-y-4">
            <FileUploader onDatasetLoad={handleDatasetLoad} />

            {datasets.length > 0 && (
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="font-semibold mb-2 flex items-center gap-2">
                  <Database className="w-5 h-5" />
                  Datasets ({datasets.length})
                </h3>
                <div className="space-y-1">
                  {datasets.map(dataset => (
                    <button
                      key={dataset.id}
                      onClick={() => setActiveDatasetId(dataset.id)}
                      className={`w-full text-left px-2 py-1 rounded text-sm ${
                        dataset.id === activeDatasetId
                          ? 'bg-blue-100 text-blue-700'
                          : 'hover:bg-gray-100'
                      }`}
                    >
                      {dataset.name}
                      <span className="text-xs text-gray-500 block">
                        {dataset.data.length} rows
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {datasets.length > 1 && (
              <JoinPanel datasets={datasets} onJoin={handleJoin} />
            )}

            {activeDataset && (
              <FilterPanel
                columns={activeDataset.columns}
                onFiltersChange={setFilters}
              />
            )}
          </div>

          <div className="lg:col-span-3">
            {activeDataset ? (
              <>
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-semibold">
                    {activeDataset.name}
                  </h2>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setViewMode('table')}
                      className={`px-3 py-1 rounded flex items-center gap-1 ${
                        viewMode === 'table'
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-200 text-gray-700'
                      }`}
                    >
                      <Table className="w-4 h-4" />
                      Table
                    </button>
                    <button
                      onClick={() => setViewMode('map')}
                      className={`px-3 py-1 rounded flex items-center gap-1 ${
                        viewMode === 'map'
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-200 text-gray-700'
                      }`}
                    >
                      <Map className="w-4 h-4" />
                      Map
                    </button>
                  </div>
                </div>

                {viewMode === 'table' ? (
                  <DataTable
                    data={filteredData}
                    columns={activeDataset.columns}
                  />
                ) : (
                  <MapView data={filteredData} />
                )}
              </>
            ) : (
              <div className="bg-white rounded-lg shadow p-12 text-center">
                <FileUp className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600 text-lg">
                  Upload CSV or Excel files to get started
                </p>
                <p className="text-gray-500 text-sm mt-2">
                  Supports automatic column standardization and data joining
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}