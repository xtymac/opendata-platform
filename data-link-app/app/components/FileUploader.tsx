'use client'

import React, { useCallback } from 'react'
import { Upload } from 'lucide-react'
import Papa from 'papaparse'
import * as XLSX from 'xlsx'
import { Dataset } from '../types'
import { standardizeColumns } from '../lib/dataProcessing'

interface FileUploaderProps {
  onDatasetLoad: (dataset: Dataset) => void
}

export default function FileUploader({ onDatasetLoad }: FileUploaderProps) {
  const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return

    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      const fileName = file.name
      const fileExt = fileName.split('.').pop()?.toLowerCase()

      if (fileExt === 'csv') {
        Papa.parse(file, {
          header: true,
          complete: (results) => {
            const { data, columns, originalColumns } = standardizeColumns(results.data as any[])
            const dataset: Dataset = {
              id: `dataset-${Date.now()}-${i}`,
              name: fileName,
              data,
              columns,
              originalColumns
            }
            onDatasetLoad(dataset)
          }
        })
      } else if (fileExt === 'xlsx' || fileExt === 'xls') {
        const reader = new FileReader()
        reader.onload = (event) => {
          const data = new Uint8Array(event.target?.result as ArrayBuffer)
          const workbook = XLSX.read(data, { type: 'array' })
          const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
          const jsonData = XLSX.utils.sheet_to_json(firstSheet)
          const { data: standardizedData, columns, originalColumns } = standardizeColumns(jsonData)
          const dataset: Dataset = {
            id: `dataset-${Date.now()}-${i}`,
            name: fileName,
            data: standardizedData,
            columns,
            originalColumns
          }
          onDatasetLoad(dataset)
        }
        reader.readAsArrayBuffer(file)
      }
    }
  }, [onDatasetLoad])

  return (
    <div className="p-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 transition-colors">
      <label className="cursor-pointer flex flex-col items-center">
        <Upload className="w-12 h-12 text-gray-400 mb-2" />
        <span className="text-sm text-gray-600">
          Click to upload CSV/Excel files
        </span>
        <input
          type="file"
          className="hidden"
          accept=".csv,.xlsx,.xls"
          multiple
          onChange={handleFileUpload}
        />
      </label>
    </div>
  )
}