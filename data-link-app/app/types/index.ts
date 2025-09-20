export interface Dataset {
  id: string
  name: string
  data: Record<string, any>[]
  columns: string[]
  originalColumns: string[]
}

export interface FilterCondition {
  column: string
  operator: 'equals' | 'contains' | 'greater' | 'less' | 'between'
  value: any
  value2?: any
}

export interface JoinConfig {
  leftDataset: string
  rightDataset: string
  leftKey: string
  rightKey: string
  joinType: 'inner' | 'left' | 'right'
}