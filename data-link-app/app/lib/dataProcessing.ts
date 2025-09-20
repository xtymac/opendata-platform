import { Dataset, FilterCondition, JoinConfig } from '../types'

const columnMappings: Record<string, string> = {
  '住所': 'address',
  '緯度': 'lat',
  '経度': 'lon',
  'longitude': 'lon',
  'latitude': 'lat',
  '市区町村コード': 'city_code',
  '名前': 'name',
  '名称': 'name',
  '人口': 'population',
  'id': 'id',
  'ID': 'id',
}

export function standardizeColumns(data: any[]): { data: any[], columns: string[], originalColumns: string[] } {
  if (!data || data.length === 0) return { data: [], columns: [], originalColumns: [] }

  const originalColumns = Object.keys(data[0])
  const columnMap = new Map<string, string>()

  originalColumns.forEach(col => {
    const standardized = columnMappings[col] || col.toLowerCase().replace(/\s+/g, '_')
    columnMap.set(col, standardized)
  })

  const standardizedData = data.map(row => {
    const newRow: any = {}
    for (const [original, standardized] of columnMap.entries()) {
      newRow[standardized] = row[original]
    }
    return newRow
  })

  return {
    data: standardizedData,
    columns: Array.from(columnMap.values()),
    originalColumns
  }
}

export function findCommonColumns(datasets: Dataset[]): string[] {
  if (datasets.length === 0) return []
  if (datasets.length === 1) return datasets[0].columns

  const commonColumns = datasets[0].columns.filter(col =>
    datasets.every(dataset => dataset.columns.includes(col))
  )

  return commonColumns
}

export function applyFilter(data: any[], condition: FilterCondition): any[] {
  return data.filter(row => {
    const value = row[condition.column]

    switch (condition.operator) {
      case 'equals':
        return value == condition.value
      case 'contains':
        return String(value).toLowerCase().includes(String(condition.value).toLowerCase())
      case 'greater':
        return Number(value) > Number(condition.value)
      case 'less':
        return Number(value) < Number(condition.value)
      case 'between':
        return Number(value) >= Number(condition.value) && Number(value) <= Number(condition.value2)
      default:
        return true
    }
  })
}

export function joinDatasets(config: JoinConfig, leftData: any[], rightData: any[]): any[] {
  const result: any[] = []

  if (config.joinType === 'inner' || config.joinType === 'left') {
    leftData.forEach(leftRow => {
      const matches = rightData.filter(rightRow =>
        leftRow[config.leftKey] == rightRow[config.rightKey]
      )

      if (matches.length > 0) {
        matches.forEach(rightRow => {
          const merged = { ...leftRow }
          Object.keys(rightRow).forEach(key => {
            if (!merged[key]) {
              merged[key] = rightRow[key]
            } else if (key !== config.rightKey) {
              merged[`right_${key}`] = rightRow[key]
            }
          })
          result.push(merged)
        })
      } else if (config.joinType === 'left') {
        result.push({ ...leftRow })
      }
    })
  }

  if (config.joinType === 'right') {
    rightData.forEach(rightRow => {
      const matches = leftData.filter(leftRow =>
        leftRow[config.leftKey] == rightRow[config.rightKey]
      )

      if (matches.length > 0) {
        matches.forEach(leftRow => {
          const merged = { ...rightRow }
          Object.keys(leftRow).forEach(key => {
            if (!merged[key]) {
              merged[key] = leftRow[key]
            } else if (key !== config.leftKey) {
              merged[`left_${key}`] = leftRow[key]
            }
          })
          result.push(merged)
        })
      } else {
        result.push({ ...rightRow })
      }
    })
  }

  return result
}