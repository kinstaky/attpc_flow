<script setup lang="ts">
import { computed, reactive, onMounted, onUnmounted } from 'vue'
import { NodeDragEvent, Connection, VueFlow, OnConnectStartParams, useVueFlow } from '@vue-flow/core'
import FlowNode from './FlowNode.vue'
import {
  activeWorkflow,
  activeWorkflowAddLink,
  activeWorkflowMoveNode,
  activeWorkflowRemoveNode,
  activeWorkflowRemoveLink,
  activeWorkflowUndo,
  activeWorkflowRedo
} from '../models/tabs'
import { type Link, createLinkFromConnection } from '../types/link'
import { interfaceColor, InterfaceType } from '../types/node'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

// Use VueFlow composable to access selection state
const { getSelectedNodes, getSelectedEdges } = useVueFlow()

// Convert workflow nodes to Vue Flow format
const vueFlowNodes = computed(() => {
  const workflow = activeWorkflow.value
  if (!workflow || !workflow.nodes) return []

  return workflow.nodes.map((node) => ({
    id: `${node.id}`,
    type: 'custom',
    position: node.position,
    data: node
  }))
})

// Convert workflow edges to Vue Flow format
const vueFlowEdges = computed(() => {
  const workflow = activeWorkflow.value
  if (!workflow || !workflow.links) return []

  return workflow.links.map((link) => {
    const source = `${link.source}`
    const sourceType = workflow.getPortBasicType(link.source, link.sourceHandle)
    const linkColor = interfaceColor[sourceType as InterfaceType]
    return {
      id: `${link.id}`,
      source: source,
      sourceHandle: link.sourceHandle,
      target: `${link.target}`,
      targetHandle: link.targetHandle,
      style: {
        stroke: linkColor,
        strokeWidth: 2,
        '--edge-color': linkColor,
      }
    }
  })
})

// linking state
const linking = reactive({
  active: false,
  node: -1,
  portType: "",
  portIndex: -1,
  dataType: "int" as InterfaceType,
})

// Handle node drag stop to save position to workflow
const handleNodeDragStop = (event: NodeDragEvent) => {
  const { node } = event
  const workflow = activeWorkflow.value
  if (!workflow) return

  // Find the node in workflow and update its position
  // const workflowNode = workflow.nodes.find(n => n.id === parseInt(node.id))
  // if (workflowNode) {
  //   workflowNode.position = { x: node.position.x, y: node.position.y }
  // }

  activeWorkflowMoveNode(parseInt(node.id), node.position)
}

// Vue Flow connection events
const handleConnect = (event: Connection) => {
  console.log('Handle Connect:', event)

  const workflow = activeWorkflow.value
  if (!workflow) return

  // Validate connection
  if (!workflow.validateLink(event)) return

  // Create connection
  const link: Link = createLinkFromConnection(workflow.lastLink, event)

  // Check if link already exists
  const linkExists = workflow.links.some(existingLink =>
    existingLink.source === link.source &&
    existingLink.sourceHandle === link.sourceHandle &&
    existingLink.target === link.target &&
    existingLink.targetHandle === link.targetHandle
  )

  if (linkExists) return

  activeWorkflowAddLink(link)

  console.log("Linked: ", workflow)
}

const handleConnectStart = (event: OnConnectStartParams) => {
  console.log("Start connect: ", event)
  const { nodeId, handleId } = event
  if (!nodeId || !handleId) return
  if (!activeWorkflow.value) return

  linking.node = parseInt(nodeId)
  const node = activeWorkflow.value.nodes[linking.node]
  if (!node) return

  const handleInfo = handleId.split("-")
  if (handleInfo.length != 2) return
  linking.portType = handleInfo[0]
  linking.portIndex = parseInt(handleInfo[1])
  if (handleInfo[0] == "input") {
    const port = node.inputs[linking.portIndex]
    linking.dataType = port.type
  } else if (handleInfo[0] == "output") {
    const port = node.outputs[linking.portIndex]
    linking.dataType = port.type
  } else if (handleInfo[0] == "property") {
    const port = node.properties[linking.portIndex]
    linking.dataType = port.type
  } else {
    return
  }
  linking.active = true
}

const handleConnectEnd = (_event: any) => {
  linking.active = false
  linking.node = -1
  linking.portIndex = -1
  linking.portType = ""
  linking.dataType = "int"
}

// Handle keyboard delete
const handleKeyDown = (event: KeyboardEvent) => {
  // Check if the event target is an input, textarea, or contenteditable element
  const target = event.target as HTMLElement
  if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.contentEditable === 'true') {
    return // Don't handle keyboard shortcuts when editing text
  }

  // Get selected nodes and edges to check if anything is selected
  const selectedNodes = getSelectedNodes.value
  const selectedEdges = getSelectedEdges.value
  const hasSelection = selectedNodes.length > 0 || selectedEdges.length > 0

  // For delete operations, only proceed if there's a selection
  const isDeleteKey = event.key === 'Delete' || event.key === 'Backspace' ||
                     (event.key === 'd' && !event.ctrlKey && !event.metaKey && !event.altKey)

  // For undo/redo, we can allow them without selection
  const isUndoKey = (event.key === 'u' && !event.ctrlKey && !event.metaKey && !event.altKey) ||
                   (event.key === 'z' && (event.ctrlKey || event.metaKey) && !event.altKey)

  const isRedoKey = (event.key === 'r' && !event.ctrlKey && !event.metaKey && !event.altKey) ||
                   ((event.key === 'y' && (event.ctrlKey || event.metaKey)) && !event.altKey)

  // Check for undo shortcuts: 'u' or 'Ctrl+z'
  if (isUndoKey) {
    event.preventDefault()
    activeWorkflowUndo()
    return
  }

  // Check for redo shortcuts: 'r' or 'Ctrl+y'
  if (isRedoKey) {
    event.preventDefault()
    activeWorkflowRedo()
    return
  }

  // Check if delete key, backspace, or 'd' is pressed (only if there's a selection)
  if (isDeleteKey && hasSelection) {
    // Prevent default behavior
    event.preventDefault()

    // Delete selected edges first
    selectedEdges.forEach(edge => {
      const linkId = parseInt(edge.id)
      if (!isNaN(linkId)) {
        activeWorkflowRemoveLink(linkId)
      }
    })

    // Then delete selected nodes
    selectedNodes.forEach(node => {
      const nodeId = parseInt(node.id)
      if (!isNaN(nodeId)) {
        activeWorkflowRemoveNode(nodeId)
      }
    })
  }
}

// Add keyboard event listener on mount
onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
})

// Remove keyboard event listener on unmount
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

</script>

<!-- <div class="canvas-wrapper" @contextmenu.prevent> -->

<template>
  <div class="canvas-wrapper">
    <!-- Vue Flow Canvas -->
    <VueFlow
      :nodes="vueFlowNodes"
      :edges="vueFlowEdges"
      :fit-view-on-init="true"
      class="vue-flow-container"
      @node-drag-stop="handleNodeDragStop"
      @connect="handleConnect"
      @connect-start="handleConnectStart"
      @connect-end="handleConnectEnd"
    >
      <!-- Custom Node Template -->
      <template #node-custom="nodeProps">
        <FlowNode
          :node-data="nodeProps.data"
          :linking="linking"
          :selected="nodeProps.selected"
        />
      </template>
    </VueFlow>
  </div>
</template>

<style scoped>
.canvas-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
}

.vue-flow-container {
  width: 100%;
  height: 100%;
  background: #1e1e1e;
}

:deep(.vue-flow__edge.selected path) {
  stroke-width: 3.5 !important;
  filter: drop-shadow(0 0 6px var(--edge-color));
}
</style>
