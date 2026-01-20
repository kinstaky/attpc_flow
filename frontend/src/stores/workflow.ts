import { reactive } from 'vue'

// Workflow-specific state (not tab state)
interface WorkflowState {
  // Add workflow-specific properties here as needed
  // For now, this can be empty or contain workflow-specific data
}

const workflowState = reactive<WorkflowState>({})

export { workflowState }
