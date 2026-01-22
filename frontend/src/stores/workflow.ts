import { type NodeData } from '../types/nodes'

// Workflow-specific state
// Workflow interface
export interface Workflow {
  name: string | null
  workspace: string | null
  nodes: NodeData[]
  // connections?: WorkflowConnection[]
}

export function emptyWorkflow() {
  return {
    name: null,
    workspace: null,
    nodes: [],
  }
}

export function defaultWorkflow(workspace: string | null) {
  return {
    name: null,
    workspace: workspace,
    nodes: [],
  }
}

export function copyWorkflow(workflow: Workflow) {
  return JSON.parse(JSON.stringify(workflow))
}