'use client'

import React, { useState } from 'react'
import { Dataset, JoinConfig } from '../types'
import { Link2 } from 'lucide-react'

interface JoinPanelProps {
  datasets: Dataset[]
  onJoin: (config: JoinConfig) => void
}

export default function JoinPanel({ datasets, onJoin }: JoinPanelProps) {
  const [config, setConfig] = useState<JoinConfig>({
    leftDataset: '',
    rightDataset: '',
    leftKey: '',
    rightKey: '',
    joinType: 'inner'
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (config.leftDataset && config.rightDataset && config.leftKey && config.rightKey) {
      onJoin(config)
    }
  }

  const leftDataset = datasets.find(d => d.id === config.leftDataset)
  const rightDataset = datasets.find(d => d.id === config.rightDataset)

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
        <Link2 className="w-5 h-5" />
        Join Datasets
      </h3>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Left Dataset
            </label>
            <select
              value={config.leftDataset}
              onChange={(e) => setConfig({ ...config, leftDataset: e.target.value, leftKey: '' })}
              className="w-full px-2 py-1 border rounded"
            >
              <option value="">Select dataset</option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Right Dataset
            </label>
            <select
              value={config.rightDataset}
              onChange={(e) => setConfig({ ...config, rightDataset: e.target.value, rightKey: '' })}
              className="w-full px-2 py-1 border rounded"
            >
              <option value="">Select dataset</option>
              {datasets.filter(d => d.id !== config.leftDataset).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Left Key
            </label>
            <select
              value={config.leftKey}
              onChange={(e) => setConfig({ ...config, leftKey: e.target.value })}
              className="w-full px-2 py-1 border rounded"
              disabled={!leftDataset}
            >
              <option value="">Select key</option>
              {leftDataset?.columns.map((col) => (
                <option key={col} value={col}>
                  {col}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Right Key
            </label>
            <select
              value={config.rightKey}
              onChange={(e) => setConfig({ ...config, rightKey: e.target.value })}
              className="w-full px-2 py-1 border rounded"
              disabled={!rightDataset}
            >
              <option value="">Select key</option>
              {rightDataset?.columns.map((col) => (
                <option key={col} value={col}>
                  {col}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Join Type
          </label>
          <select
            value={config.joinType}
            onChange={(e) => setConfig({ ...config, joinType: e.target.value as any })}
            className="w-full px-2 py-1 border rounded"
          >
            <option value="inner">Inner Join</option>
            <option value="left">Left Join</option>
            <option value="right">Right Join</option>
          </select>
        </div>

        <button
          type="submit"
          className="w-full bg-green-500 text-white py-2 rounded hover:bg-green-600"
        >
          Join Datasets
        </button>
      </form>
    </div>
  )
}