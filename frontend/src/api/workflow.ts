import { activeTabName, activeWorkflow } from '../stores/tabs'

// API base URL
const API_BASE = ''

// Create new workflow via POST API
export const createWorkflow = async (): Promise<void> => {
  const response = await fetch(`${API_BASE}/workflows`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(activeWorkflow.value)
  })

  if (!response.ok) {
    throw new Error(`Failed to create workflow: ${response.statusText}`)
  }
}

// Update existing workflow via PUT API
export const updateWorkflow = async (): Promise<void> => {
  if (!activeWorkflow.value) {
    throw new Error('No active workflow to update')
  }
  console.log(activeWorkflow.value)
  const response = await fetch(
    `${API_BASE}/workflows/${encodeURIComponent(activeWorkflow.value.name!)}`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(activeWorkflow.value)
    }
  )
  if (!response.ok) {
    throw new Error(`Failed to update workflow: ${response.statusText}`)
  }
}

// Delete workflow via DELETE API
export const deleteWorkflow = async (): Promise<void> => {
  const response = await fetch(
    `${API_BASE}/workflows/${encodeURIComponent(activeTabName.value!)}`,
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
export const getWorkflow = async (workflowName: string) => {
  const response = await fetch(`${API_BASE}/workflows/${workflowName}`)
  if (!response.ok) {
    throw new Error(`Failed to get workflow: ${response.statusText}`)
  }
  return await response.json()
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