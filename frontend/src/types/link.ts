import { Connection } from "@vue-flow/core";
import { type Workflow } from "../stores/workflow";
import { basicType } from "./nodes";

// Connection types
export interface Link {
	id: number,
	source: number,
	sourceHandle: string,
	target: number,
	targetHandle: string,
}

export const getPortType = (workflow: Workflow, nodeId: string, port: string) => {
  const node = workflow.nodes[parseInt(nodeId)]
  if (!node) return null
  if (port.startsWith("input")) {
    const portId = parseInt(port.replace("input-", ""))
    return node.inputs[portId].type
  } else if (port.startsWith("output")) {
    const portId = parseInt(port.replace("output-", ""))
    return node.outputs[portId].type
  } else if (port.startsWith("property")) {
    const portId = parseInt(port.replace("property-", ""))
    return node.properties[portId].type
  }
  return null
}

export const getPortBasicType = (workflow: Workflow, nodeId: string, port: string) => {
  return basicType(getPortType(workflow, nodeId, port)!)
}

export const validateLink = (workflow: Workflow, connection: Connection) => {
  const { source, sourceHandle, target, targetHandle } = connection
  if (source == target) return false
  if (!sourceHandle || !targetHandle) return false

  if (!sourceHandle.startsWith("output")) return false;
  if (!targetHandle.startsWith("input") && !targetHandle.startsWith("property")) return false;
  const sourceType = getPortType(workflow, source, sourceHandle)
  const targetType = getPortType(workflow, target, targetHandle)
  if (!sourceType || !targetType) return false

  return sourceType == targetType
}

export const createLinkFromConnection = (id: number, connection: Connection) => {
  return {
    id: id,
    source: parseInt(connection.source),
    sourceHandle: connection.sourceHandle!,
    target: parseInt(connection.target),
    targetHandle: connection.targetHandle!,
  }
}