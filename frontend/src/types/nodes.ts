export interface NodeData {
    name: string,
	positon: { x: number, y: number },
	inputs: NodeInput[],
	outputs: NodeOutput[],
	properties: NodeProperty[],
}


export interface NodeInput {
	name: string,
	type: InterfaceType,
}

export interface NodeOutput {
	name: string,
	type: InterfaceType,
}

export interface NodeProperty {
	name: string,
	type: InterfaceType,
	value: any,
}

export type InterfaceType =
	"bool" | "int" | "float" | "str" | "bool[]" | "int[]" | "float[]" | "str[]"
