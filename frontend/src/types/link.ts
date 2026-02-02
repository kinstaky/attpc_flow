import { Connection } from "@vue-flow/core";

// Connection types
export interface Link {
	id: number,
	source: number,
	sourceHandle: string,
	target: number,
	targetHandle: string,
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