'use client'

import React, { useState } from 'react'
import { FilterCondition } from '../types'
import { Filter, Plus, Trash2 } from 'lucide-react'

interface FilterPanelProps {
  columns: string[]
  onFiltersChange: (filters: FilterCondition[]) => void
}

export default function FilterPanel({ columns, onFiltersChange }: FilterPanelProps) {
  const [filters, setFilters] = useState<FilterCondition[]>([])

  const addFilter = () => {
    const newFilter: FilterCondition = {
      column: columns[0] || '',
      operator: 'equals',
      value: ''
    }
    const updatedFilters = [...filters, newFilter]
    setFilters(updatedFilters)
    onFiltersChange(updatedFilters)
  }

  const updateFilter = (index: number, field: keyof FilterCondition, value: any) => {
    const updatedFilters = [...filters]
    updatedFilters[index] = { ...updatedFilters[index], [field]: value }
    setFilters(updatedFilters)
    onFiltersChange(updatedFilters)
  }

  const removeFilter = (index: number) => {
    const updatedFilters = filters.filter((_, i) => i !== index)
    setFilters(updatedFilters)
    onFiltersChange(updatedFilters)
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Filter className="w-5 h-5" />
          Filters
        </h3>
        <button
          onClick={addFilter}
          className="bg-blue-500 text-white px-3 py-1 rounded hover:bg-blue-600 flex items-center gap-1"
        >
          <Plus className="w-4 h-4" />
          Add Filter
        </button>
      </div>

      <div className="space-y-2">
        {filters.map((filter, index) => (
          <div key={index} className="flex gap-2 p-2 bg-gray-50 rounded">
            <select
              value={filter.column}
              onChange={(e) => updateFilter(index, 'column', e.target.value)}
              className="px-2 py-1 border rounded"
            >
              {columns.map((col) => (
                <option key={col} value={col}>
                  {col}
                </option>
              ))}
            </select>

            <select
              value={filter.operator}
              onChange={(e) => updateFilter(index, 'operator', e.target.value as any)}
              className="px-2 py-1 border rounded"
            >
              <option value="equals">Equals</option>
              <option value="contains">Contains</option>
              <option value="greater">Greater than</option>
              <option value="less">Less than</option>
              <option value="between">Between</option>
            </select>

            <input
              type="text"
              value={filter.value}
              onChange={(e) => updateFilter(index, 'value', e.target.value)}
              placeholder="Value"
              className="px-2 py-1 border rounded flex-1"
            />

            {filter.operator === 'between' && (
              <input
                type="text"
                value={filter.value2 || ''}
                onChange={(e) => updateFilter(index, 'value2', e.target.value)}
                placeholder="Value 2"
                className="px-2 py-1 border rounded flex-1"
              />
            )}

            <button
              onClick={() => removeFilter(index)}
              className="text-red-500 hover:text-red-700"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}