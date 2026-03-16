export interface Position {
	x: number,
	y: number,
}

export interface Node {
    id: number,
	name: string,
	position: Position,
	inputs: NodeInput[],
	outputs: NodeOutput[],
	properties: NodeProperty[],
}

export type NodeInput = NodePort
export type NodeOutput = NodePort

export interface NodePort {
	name: string,
	type: InterfaceType,
	links: number[],
}

export interface NodeProperty {
	name: string,
	type: InterfaceType,
	value: string,
	links: number[],
}

export type InterfaceType =
	"bool" | "int" | "float" | "str" | "bool[]" | "int[]" | "float[]" | "str[]" | "matrix" | "matrix[]"

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
	"matrix": "#C11780",
	"matrix[]": "#C11780",
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
	"matrix": "#E02799",
	"matrix[]": "#E02799",
	// blue: #2196F3
	// indigo: #3F51B5
	// deep orange: #FF5722
	// pink: #CE1788
	// brown: #795548
}

// export const linkPort = (node: Node, portHandle: string, linkId) => {
// 	if (!portHandle.startsWith("port-")) return
// 	node.inputs[parseInt(portHandle.replace("port-", ""))].linked = true
// }

// export const linkProperty = (node: Node, propertyHandle: string) => {
// 	if (!propertyHandle.startsWith("property-")) return
// 	node.properties[parseInt(propertyHandle.replace("property-", ""))].linked = true
// }

// export const unlinkProperty = (node: Node, propertyHandle: string) => {
// 	if (!propertyHandle.startsWith("property-")) return
// 	node.properties[parseInt(propertyHandle.replace("property-", ""))].linked = false
// }

const adaptNodePorts = (ports: Record<string, string> | null) => {
  if (!ports) return []
  return Object.entries(ports).map(([name, type]) => {
    return {
      name: name,
      type: type,
	  links: [],
    } as NodePort
  })
}

const adaptNodeProperties = (properties: Record<string, string> | null) => {
  if (!properties) return []
  return Object.entries(properties).map(([name, type]) => {
    return {
      name: name,
      type: type,
      value: "",
      links: [],
    } as NodeProperty
  })
}

export const parseNode = (json: any, position: { x: number, y: number }): Node => {
	return {
		id: -1,
		name: json.name,
		position: position,
		inputs: adaptNodePorts(json.inputs),
		outputs: adaptNodePorts(json.outputs),
		properties: adaptNodeProperties(json.properties),
	}
}