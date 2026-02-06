const API_BASE = ''

export interface RunInfo {
  run: number
  start: number
  stop: number
  duration: number
  [key: string]: string | number
}

export interface RunFilterRequest {
  runs?: number[]
  tags?: string[]
}


export const getRuns = async (workspace: string): Promise<number[]> => {
  const response = await fetch(`${API_BASE}/runs?workspace=${encodeURIComponent(workspace)}`)
  if (!response.ok) {
    throw new Error(`Failed to list runs: ${response.statusText}`)
  }
  return await response.json()
}

export const getTags = async (workspace: string): Promise<Record<string, string[]>> => {
  const response = await fetch(`${API_BASE}/runs/tags?workspace=${encodeURIComponent(workspace)}`)
  if (!response.ok) {
    throw new Error(`Failed to get tags: ${response.statusText}`)
  }
  return await response.json()
}

export const getRunsInfo = async (workspace: string, runs?: number[]): Promise<RunInfo[]> => {
  let url = `${API_BASE}/runs/info?workspace=${encodeURIComponent(workspace)}`
  if (runs && runs.length > 0) {
    url += `&runs=${runs.join(',')}`
  }
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Failed to get runs info: ${response.statusText}`)
  }
  return await response.json()
}

export const getRunInfo = async (workspace: string, runNumber: number): Promise<RunInfo> => {
  const response = await fetch(`${API_BASE}/runs/${runNumber}?workspace=${encodeURIComponent(workspace)}`)
  if (!response.ok) {
    throw new Error(`Failed to get run info: ${response.statusText}`)
  }
  return await response.json()
}

export const refreshRuns = async (workspace: string | null): Promise<void> => {
  if (!workspace) return
  const response = await fetch(`${API_BASE}/runs/refresh?workspace=${encodeURIComponent(workspace)}`, {
    method: 'POST'
  })
  if (!response.ok) {
    console.error(`Failed to refresh database: ${response.statusText}`)
  }
}

