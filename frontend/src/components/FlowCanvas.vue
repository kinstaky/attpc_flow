<script setup lang="ts">
import { computed } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import FlowNode from './FlowNode.vue'
import { activeWorkflow } from '../stores/tabs'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

// Vue Flow setup
const { onConnect } = useVueFlow()

// Handle node drag stop to save position to workflow
const handleNodeDragStop = (event: any) => {
  const { node } = event
  const workflow = activeWorkflow.value
  if (!workflow) return

  // Find the node in workflow and update its position
  const workflowNode = workflow.nodes.find(n => n.id === parseInt(node.id.replace('node-', '')))
  if (workflowNode) {
    workflowNode.position = { x: node.position.x, y: node.position.y }
  }

  console.log('Node dragged:', node)
}

// Convert workflow nodes to Vue Flow format
const vueFlowNodes = computed(() => {
  const workflow = activeWorkflow.value
  if (!workflow || !workflow.nodes) return []

  return workflow.nodes.map((node) => ({
    id: `node-${node.id}`,
    type: 'custom',
    position: node.position,
    data: node
  }))
})

// Vue Flow events
onConnect((event) => {
  console.log('Connection made:', event)
})
</script>

<!-- <div class="canvas-wrapper" @contextmenu.prevent> -->

<template>
  <div class="canvas-wrapper">
    <!-- Vue Flow Canvas -->
    <VueFlow
      :nodes="vueFlowNodes"
      :fit-view-on-init="true"
      :snap-to-grid="true"
      :snap-grid="[20, 20]"
      class="vue-flow-container"
      @node-drag-stop="handleNodeDragStop"
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
