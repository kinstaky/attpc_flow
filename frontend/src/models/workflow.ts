import { type Node, type InterfaceType, type Position } from '../types/node'
import { type Link } from '../types/link'
import { type Connection } from '@vue-flow/core'

export interface WorkflowRun {
  runs: number[];
  tags: string[];
}

// Workflow interface
export class Workflow {
  name: string;
  workspace: string | null;
  workers: number;
  run: WorkflowRun;
  nodes: Node[];
  links: Link[];
  lastNode: number;
  lastLink: number;

  constructor(
    name: string,
    workspace: string | null = null,
    workers: number = 2,
    run: WorkflowRun = {runs: [], tags: []},
    nodes: Node[] = [],
    links: Link[] = [],
    lastNode: number = 0,
    lastLink: number = 0
  ) {
    this.name = name
    this.workspace = workspace || null
    this.workers = workers
    this.run = run
    this.nodes = nodes
    this.links = links
    this.lastNode = lastNode
    this.lastLink = lastLink
  }

  // Deep copy method
  copy(newName?: string): Workflow {
    // Deep copy nodes and links
    const deepCopyNodes = this.nodes.map(node => ({ ...node }))
    const deepCopyLinks = this.links.map(link => ({ ...link }))

    return new Workflow(
      newName || this.name,
      this.workspace,
      this.workers,
      this.run,
      deepCopyNodes,
      deepCopyLinks,
      this.lastNode,
      this.lastLink
    )
  }

  changeName(newName: string): string {
    let oldName = this.name
    this.name = newName
    return oldName
  }

  changeWorkspace(newWorkspace: string | null): string | null {
    let oldWorkspace = this.workspace
    this.workspace = newWorkspace
    return oldWorkspace
  }

  changeWorkers(newWorkers: number): number {
    let oldWorkers = this.workers
    this.workers = newWorkers
    return oldWorkers
  }

  changeRun(newRun: WorkflowRun): WorkflowRun {
    let oldRun = this.run
    this.run = newRun
    return oldRun
  }

  pushNode(node: Node): void {
    node.id = this.lastNode
    this.nodes.push(node)
    this.lastNode += 1
  }

  popNode(): Node | null {
    if (this.nodes.length === 0) return null
    let node = this.nodes.pop()!
    this.lastNode -= 1
    return node
  }

  insertNode(index: number, node: Node): void {
    this.nodes.splice(index, 0, node)
  }

  removeNode(nodeId: number): [number, Node] | null {
    let idx = this.nodes.findIndex(n => n.id == nodeId)
    if (idx === -1) return null
    let removed = this.nodes[idx]
    this.nodes.splice(idx, 1)
    return [idx, removed]
  }

  moveNode(nodeId: number, position: Position): Position | null {
    const node = this.nodes.find(n => n.id == nodeId)
    if (!node) return null
    const oldPosition = node.position
    node.position = position
    return oldPosition
  }

  getPortType(nodeId: number, port: string): InterfaceType | null {
    const node = this.nodes.find(n => n.id == nodeId)
    if (!node) return null
    if (port.startsWith("input")) {
      return node.inputs[parseInt(port.split("-")[1])].type
    } else if (port.startsWith("output")) {
      return node.outputs[parseInt(port.split("-")[1])].type
    } else if (port.startsWith("property")) {
      return node.properties[parseInt(port.split("-")[1])].type
    }
    return null
  }

  getPortBasicType(nodeId: number, port: string): InterfaceType | null {
    return this.getPortType(nodeId, port)?.replace("[]", "") as InterfaceType
  }

  validateLink(connection: Connection): boolean {
    const { source, sourceHandle, target, targetHandle } = connection

    if (source == target) return false
    if (!sourceHandle || !targetHandle) return false
    if (!sourceHandle.startsWith("output")) return false;
    if (
      !targetHandle.startsWith("input") &&
      !targetHandle.startsWith("property")
    ) return false;

    const sourceType = this.getPortType(parseInt(source), sourceHandle)
    const targetType = this.getPortType(parseInt(target), targetHandle)
    if (!sourceType || !targetType) return false

    return sourceType == targetType
  }

  updateNodeLink(link: Link, add: boolean): void {
    const sourceNode = this.nodes.find(n => n.id == link.source)
    const targetNode = this.nodes.find(n => n.id == link.target)
    if (!sourceNode || !targetNode) return
    const sourcePortIndex = parseInt(link.sourceHandle.split("-")[1])
    const sourcePort = sourceNode.outputs[sourcePortIndex]
    const targetPortIndex = parseInt(link.targetHandle.split("-")[1])
    const targetPort = link.targetHandle.startsWith("input")
      ? targetNode.inputs[targetPortIndex]
      : targetNode.properties[targetPortIndex]
    if (add) {
      sourcePort.links.push(link.id)
      targetPort.links.push(link.id)
    } else {
      sourcePort.links.splice(sourcePort.links.indexOf(link.id), 1)
      targetPort.links.splice(targetPort.links.indexOf(link.id), 1)
    }
  }

  pushLink(link: Link): void {
    link.id = this.lastLink
    this.links.push(link)
    this.lastLink += 1
    this.updateNodeLink(link, true)
  }

  popLink(): Link | null {
    if (this.links.length === 0) return null
    let link = this.links.pop()!
    this.lastLink -= 1
    this.updateNodeLink(link, false)
    return link
  }

  insertLink(index: number, link: Link): void {
    this.links.splice(index, 0, link)
    this.updateNodeLink(link, true)
  }

  removeLink(linkId: number): [number, Link] | null {
    let idx = this.links.findIndex(l => l.id == linkId)
    if (idx === -1) return null
    let removed = this.links[idx]
    this.links.splice(idx, 1)
    this.updateNodeLink(removed, false)
    return [idx, removed]
  }
}