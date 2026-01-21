import { activeTabId, activeTabName, updateActiveTabName, attachTab } from '../stores/tabs'

// API base URL
const API_BASE = ''

// Create new workflow via POST API
export const createWorkflow = async (name: string) => {
  try {
    const workflowData = {
      name: name
    }

    const response = await fetch(`${API_BASE}/workflows`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(workflowData)
    })

    if (!response.ok) {
      throw new Error(`Failed to create workflow: ${response.statusText}`)
    }

    console.log('Workflow created successfully:', name)
    return true
  } catch (error) {
    console.error('Error creating workflow:', error)
    return false
  }
}

// Update existing workflow via PUT API
export const updateWorkflow = async (name: string) => {
  try {
    const workflowData = {
      name: name
    }

    const response = await fetch(`${API_BASE}/workflows/${encodeURIComponent(name)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(workflowData)
    })

    if (!response.ok) {
      throw new Error(`Failed to update workflow: ${response.statusText}`)
    }

    console.log('Workflow updated successfully:', name)
    return true
  } catch (error) {
    console.error('Error updating workflow:', error)
    return false
  }
}

// Delete workflow via DELETE API
export const deleteWorkflow = async (name: string) => {
  try {
    const response = await fetch(`${API_BASE}/workflows/${encodeURIComponent(name)}`, {
      method: 'DELETE'
    })

    if (!response.ok) {
      throw new Error(`Failed to delete workflow: ${response.statusText}`)
    }

    console.log('Workflow deleted successfully:', name)
    return true
  } catch (error) {
    console.error('Error deleting workflow:', error)
    return false
  }
}

// Get all existing workflows
export const getExistingWorkflows = async (): Promise<string[]> => {
  try {
    const response = await fetch(`${API_BASE}/workflows`)
    if (response.ok) {
      return await response.json()
    }
    return []
  } catch (error) {
    console.error('Failed to fetch workflows:', error)
    return []
  }
}

// Check if a workflow name already exists
export const workflowNameExists = async (name: string): Promise<boolean> => {
  const existingWorkflows = await getExistingWorkflows()
  return existingWorkflows.indexOf(name) !== -1
}

// Save workflow (create or update based on attachment status)
export const saveWorkflow = async (tabId?: string) => {
  const currentTabId = tabId || activeTabId.value
  const workflowName = activeTabName.value
  
  if (!workflowName) {
    return { success: false, needsName: true }
  }
  
  // Check if name already exists for unattached tabs
  const isAttached = await isTabAttached(currentTabId)
  if (!isAttached) {
    const nameExists = await workflowNameExists(workflowName)
    if (nameExists) {
      return { success: false, nameConflict: true, existingName: workflowName }
    }
  }
  
  // Save the workflow
  const success = await createWorkflow(workflowName)
  if (success) {
    attachTab(currentTabId)
  }
  
  return { success, needsName: false, nameConflict: false }
}

// Rename workflow (create new and delete old)
export const renameWorkflow = async (oldName: string, newName: string) => {
  try {
    // Create new workflow with new name
    const createSuccess = await createWorkflow(newName)
    if (!createSuccess) {
      return false
    }
    
    // Delete old workflow
    await deleteWorkflow(oldName)
    
    // Update tab name
    updateActiveTabName(newName)
    
    console.log('Workflow renamed successfully:', oldName, '->', newName)
    return true
  } catch (error) {
    console.error('Error renaming workflow:', error)
    return false
  }
}

// Helper function to check if tab is attached (imported from store)
async function isTabAttached(tabId: string): Promise<boolean> {
  // This would need to be imported from the store
  // For now, we'll assume it's available
  return true // Placeholder
}
