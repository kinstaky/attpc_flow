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
	type: InterfaceType,
	value: any,
	linked: boolean,
}

export type InterfaceType =
	"bool" | "int" | "float" | "str" | "bool[]" | "int[]" | "float[]" | "str[]"

export const basicType = (t: InterfaceType) => t.split("[")[0]

export const isArrayType = (t: InterfaceType) => t.includes("[")

export const interfaceColor: Record<InterfaceType, string> = {
	"int": "#4CAF50",
	"int[]": "#4CAF50",
	"float": "#FF9800",
	"float[]": "#FF9800",
	"bool": "#9C27B0",
	"bool[]": "#9C27B0",
	"str": "#1EADC0",
	"str[]": "#1EADC0",
	// blue: #2196F3
	// indigo: #3F51B5
	// deep orange: #FF5722
	// pink: #CE1788
	// brown: #795548
}

export const interfaceHoverColor: Record<InterfaceType, string> = {
	"int": "#74EE78",
	"int[]": "#74EE78",
	"float": "#FFA600",
	"float[]": "#FFA600",
	"bool": "#C430DF",
	"bool[]": "#C430DF",
	"str": "#24DEF7",
	"str[]": "#24DEF7",
}

export const linkProperty = (node: NodeData, propertyHandle: string) => {
	if (!propertyHandle.startsWith("property-")) return
	node.properties[parseInt(propertyHandle.replace("property-", ""))].linked = true
}