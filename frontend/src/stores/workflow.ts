import { type NodeData } from '../types/nodes'
import { type Link } from '../types/link'

// Workflow interface
export interface Workflow {
  name: string | null
  workspace: string | null
  workers: number
  nodes: NodeData[]
  links: Link[]
  lastNode: number
  lastLink: number
}

export function defaultWorkflow(workspace?: string | null) {
  return {
    name: null,
    workspace: workspace || null,
    workers: 2,
    nodes: [],
    links: [],
    lastNode: 0,
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