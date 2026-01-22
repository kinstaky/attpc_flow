export interface NodeData {
    id: number,
	name: string,
	position: { x: number, y: number },
	inputs: NodeInput[],
	outputs: NodeOutput[],
	properties: NodeProperty[],
}


export type NodeInput = NodePort
export type NodeOutput = NodePort

export interface NodePort {
	name: string,
	type: InterfaceType,
}

export interface NodeProperty {
	name: string,
	type: InterfaceType | "connection",
	value: any,
}

export type InterfaceType =
	"bool" | "int" | "float" | "str" | "bool[]" | "int[]" | "float[]" | "str[]"