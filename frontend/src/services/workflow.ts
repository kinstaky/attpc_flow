import { activeTabId, updateActiveTabName, saveTab, activeTabName, activeWorkflow } from '../stores/tabs'
import { type Workflow } from '../stores/workflow'

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

// List workflows
export const listWorkflows = async (): Promise<string[]> => {
  const response = await fetch(`${API_BASE}/workflows`)
  if (!response.ok) {
    throw new Error(`Failed to fetch workflows: ${response.statusText}`)
  }
  const workflows = await response.json()
  return workflows
}

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

// // Save workflow (used when closing unnamed tabs)
// export const saveWorkflow = async (workflowName: string, workspace?: string | null) => {
//   const currentTabId = activeTabId.value
//   const isAttached = isTabAttached(currentTabId)

//   if (!isAttached) {
//     const nameExists = await workflowNameExists(workflowName)
//     if (nameExists) {
//       return { success: false, nameConflict: true, existingName: workflowName }
//     }
//   }

//   // Save the workflow
//   const workflow = {
//     name: workflowName,
//     workspace: workspace || null
//   }
//   const success = await createWorkflow(workflow)
//   if (success) {
//     saveTab(currentTabId)
//   }

//   return { success, needsName: false, nameConflict: false }
// }

// // Rename workflow (create new and delete old)
// export const renameWorkflow = async (oldName: string, newName: string, workspace?: string | null) => {
//   // Create new workflow with new name
//   const workflow = {
//     name: newName,
//     workspace: workspace || null
//   }
//   const createSuccess = await createWorkflow(workflow)
//   if (!createSuccess) {
//     return false
//   }

//   // Delete old workflow
//   await deleteWorkflow(oldName)

//   // Update tab name
//   updateActiveTabName(newName)
// }

// // Helper function to check if tab is attached (imported from store)
// async function isTabAttached(tabId: string): Promise<boolean> {
//   // This would need to be imported from the store
//   // For now, we'll assume it's available
//   return true // Placeholder
// }
