import { type NodeData } from '../types/nodes'
import { type Link } from '../types/link'

// Workflow interface
export interface Workflow {
  name: string | null
  workspace: string | null
  nodes: NodeData[]
  links: Link[]
  lastNode: number
  lastLink: number
}

export function defaultWorkflow(workspace?: string | null) {
  return {
    name: null,
    workspace: workspace || null,
    nodes: [],
    lastNode: 0,
    links: [],
    lastLink: 0,
  }
}

export function copyWorkflow(workflow: Workflow, newName?: string) {
  const newWorkflow = JSON.parse(JSON.stringify(workflow))
  if (newName) {
    newWorkflow.name = newName
  }
  return newWorkflow
}