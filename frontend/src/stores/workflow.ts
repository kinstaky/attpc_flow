import { reactive } from 'vue'

// Workflow-specific state
// Workflow interface
export interface Workflow {
  name: string | null
  workspace: string | null
  // Add other workflow properties as needed
  // nodes?: WorkflowNode[]
  // connections?: WorkflowConnection[]
}