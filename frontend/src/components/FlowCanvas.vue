<script setup lang="ts">
import { computed } from 'vue'
import { NodeDragEvent, Connection, VueFlow } from '@vue-flow/core'
import FlowNode from './FlowNode.vue'
import { activeWorkflow } from '../stores/tabs'
import { type Link, validateLink, createLinkFromConnection, getPortBasicType } from '../types/link'
import { interfaceColor, InterfaceType, linkProperty } from '../types/nodes'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

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
    const sourceType = getPortBasicType(workflow, source, link.sourceHandle)
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
      }
    }
  })
})

// Handle node drag stop to save position to workflow
const handleNodeDragStop = (event: NodeDragEvent) => {
  const { node } = event
  const workflow = activeWorkflow.value
  if (!workflow) return

  // Find the node in workflow and update its position
  const workflowNode = workflow.nodes.find(n => n.id === parseInt(node.id))
  if (workflowNode) {
    workflowNode.position = { x: node.position.x, y: node.position.y }
  }
}

// Vue Flow connection events
const handleConnect = (event: Connection) => {
  console.log('Handle Connect:', event)

  console.log(activeWorkflow.value)
  const workflow = activeWorkflow.value
  if (!workflow) return


  // Validate connection
  if (!validateLink(workflow, event)) return

  // Create connection
  const link: Link = createLinkFromConnection(workflow.lastLink, event)

  // Add to workflow
  workflow.links.push(link)
  ++workflow.lastLink

  linkProperty(workflow.nodes[link.target], link.targetHandle)

  console.log("Linked: ", workflow)
}

const handleConnectEnd = (_event: any) => {
  // console.log('Connection ended:')
}

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
      @connect-end="handleConnectEnd"
    >
      <!-- Custom Node Template -->
      <template #node-custom="nodeProps">
        <FlowNode :node-data="nodeProps.data" />
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
</style>
