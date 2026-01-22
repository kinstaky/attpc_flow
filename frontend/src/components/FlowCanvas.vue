<script setup lang="ts">
import { computed } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import FlowNode from './FlowNode.vue'
import { activeWorkflow } from '../stores/tabs'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

// Vue Flow setup
const { onNodeDragStop, onConnect } = useVueFlow()

// Convert workflow nodes to Vue Flow format
const vueFlowNodes = computed(() => {
  const workflow = activeWorkflow.value
  if (!workflow || !workflow.nodes) return []

  return workflow.nodes.map((node, index) => ({
    id: `node-${index}`,
    type: 'custom',
    position: node.position,
    data: node
  }))
})

// Vue Flow events
onNodeDragStop((event) => {
  console.log('Node dragged:', event)
})

onConnect((event) => {
  console.log('Connection made:', event)
})
</script>

<template>
  <div class="canvas-wrapper" @contextmenu.prevent>
    <!-- Vue Flow Canvas -->
    <VueFlow
      v-model:nodes="vueFlowNodes"
      :fit-view-on-init="true"
      :snap-to-grid="true"
      :snap-grid="[20, 20]"
      class="vue-flow-container"
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
