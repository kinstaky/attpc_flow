import { Workflow } from '../models/workflow'

// API base URL
const API_BASE = ''

// Create new workflow via POST API
export const createWorkflow = async (workflow: Workflow): Promise<void> => {
  const response = await fetch(`${API_BASE}/workflows`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(workflow)
  })

  if (!response.ok) {
    throw new Error(`Failed to create workflow: ${response.statusText}`)
  }
}

// Update existing workflow via PUT API
export const updateWorkflow = async (workflow: Workflow): Promise<void> => {
  const response = await fetch(
    `${API_BASE}/workflows/${encodeURIComponent(workflow.name)}`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(workflow)
    }
  )
  if (!response.ok) {
    throw new Error(`Failed to update workflow: ${response.statusText}`)
  }
}

// Delete workflow via DELETE API
export const deleteWorkflow = async (workflowName: string): Promise<void> => {
  const response = await fetch(
    `${API_BASE}/workflows/${encodeURIComponent(workflowName)}`,
    {
      method: 'DELETE'
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to delete workflow: ${response.statusText}`)
  }
}

// List workflows via GET API
export const listWorkflows = async (): Promise<string[]> => {
  const response = await fetch(`${API_BASE}/workflows`)
  if (!response.ok) {
    throw new Error(`Failed to fetch workflows: ${response.statusText}`)
  }
  const workflows = await response.json()
  return workflows
}

// get specific workflow via GET API
export const getWorkflow = async (workflowName: string): Promise<Workflow> => {
  const response = await fetch(`${API_BASE}/workflows/${encodeURIComponent(workflowName)}`)
  if (!response.ok) {
    throw new Error(`Failed to get workflow: ${response.statusText}`)
  }
  const data = await response.json()
  return new Workflow(
    data.name,
    data.workspace,
    data.workers,
    data.run || {runs: [], tags: []},
    data.nodes || [],
    data.links || [],
    data.lastNode || 0,
    data.lastLink || 0
  )
}

// Check if a workflow name already exists
export const workflowNameExists = async (name: string): Promise<boolean> => {
  const existingWorkflows = await listWorkflows()
  return existingWorkflows.indexOf(name) !== -1
}

// Execute workflow via POST API
export const executeWorkflow = async (workflowName: string) => {
  const response = await fetch(`${API_BASE}/executions/${encodeURIComponent(workflowName)}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    }
  })

  if (!response.ok) {
    throw new Error(`Failed to execute workflow: ${response.statusText}`)
  }

  return await response.json()
}

// List executions via GET API
export const listExecutions = async () => {
  const response = await fetch(`${API_BASE}/executions`)
  if (!response.ok) {
    throw new Error(`Failed to fetch executions: ${response.statusText}`)
  }
  return await response.json()
}