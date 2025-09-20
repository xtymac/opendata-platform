'use client'

import React from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'

interface DataTableProps {
  data: any[]
  columns: string[]
  pageSize?: number
}

export default function DataTable({ data, columns, pageSize = 10 }: DataTableProps) {
  const [page, setPage] = React.useState(0)

  const totalPages = Math.ceil(data.length / pageSize)
  const paginatedData = data.slice(page * pageSize, (page + 1) * pageSize)

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        No data to display
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {paginatedData.map((row, idx) => (
              <tr key={idx} className="hover:bg-gray-50">
                {columns.map((col) => (
                  <td key={col} className="px-4 py-2 text-sm text-gray-900">
                    {row[col] !== null && row[col] !== undefined
                      ? String(row[col])
                      : ''}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="px-4 py-3 bg-gray-50 border-t flex items-center justify-between">
          <div className="text-sm text-gray-700">
            Showing {page * pageSize + 1} to {Math.min((page + 1) * pageSize, data.length)} of {data.length} results
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="p-1 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="px-3 py-1">
              Page {page + 1} of {totalPages}
            </span>
            <button
              onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
              disabled={page === totalPages - 1}
              className="p-1 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}