<script setup lang="ts">
import { computed, ref } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import type { NodeData } from '../types/nodes'

interface Props {
  nodeData: NodeData
}

const props = defineProps<Props>()

// Constants for node layout
const nodeWidth = 360

// Handle array input for str[] type
// const arrayStringValues = ref<Record<number, string>>({})

// const updateArrayValue = (index: number, value: string) => {
//   // Convert comma-separated string to array
//   const array = value.split(',').map(item => item.trim()).filter(item => item)
//   // Update the property value
//   const property = props.nodeData.properties[index]
//   if (property) {
//     property.value = array
//   }
// }

// // Initialize array string values
// props.nodeData.properties.forEach((property, index) => {
//   if (property.type === 'str[]') {
//     if (Array.isArray(property.value)) {
//       arrayStringValues.value[index] = property.value.join(', ')
//     } else {
//       arrayStringValues.value[index] = ''
//     }
//   }
// })

// Get max number of ports to align rows
const maxPorts = computed(() => Math.max(props.nodeData.inputs.length, props.nodeData.outputs.length))
</script>

<template>
  <v-card class="flow-node" :style="{ width: nodeWidth + 'px' }" elevation="2">
    <!-- Node Title -->
    <v-card-title class="node-title pa-2 text-center">
      {{ nodeData.name }}
    </v-card-title>

    <v-divider></v-divider>

    <!-- Inputs and Outputs Section -->
    <v-card-text class="pa-2">
      <v-row
        v-for="index in maxPorts"
        :key="`port-row-${index}`"
        class="port-row ma-0"
        align="center"
        dense
      >
        <!-- Input Port (Left) -->
        <v-col cols="5" class="pa-1" v-if="index <= nodeData.inputs.length">
          <div class="port-container port-input-container">
            <div class="port-handle">
              <Handle
                :id="`input-${index - 1}`"
                type="target"
                :position="Position.Left"
              />
            </div>
            <span class="port-label">{{ nodeData.inputs[index - 1]?.name ?? '' }}</span>
          </div>
        </v-col>
        <v-col cols="5" v-else class="pa-1"></v-col>

        <!-- Spacer -->
        <v-col cols="2" class="pa-0"></v-col>

        <!-- Output Port (Right) -->
        <v-col cols="5" class="pa-1" v-if="index <= nodeData.outputs.length">
          <div class="port-container port-output-container">
            <span class="port-label">{{ nodeData.outputs[index - 1]?.name ?? '' }}</span>
              <div class="port-handle">
                <Handle
                  :id="`output-${index - 1}`"
                  type="source"
                  :position="Position.Right"
                />
              </div>
          </div>
        </v-col>
        <v-col cols="5" v-else class="pa-1"></v-col>
      </v-row>
      <v-row
        v-for="(property, index) in nodeData.properties"
        :key="`property-${index}`"
        class="property-row ma-0"
        align="center"
        justify="start"
        dense
      >
        <v-col cols="1" class="pa-1">
          <div class="property-handle">
            <Handle
              :id="`property-${index - 1}`"
              type="target"
              :position="Position.Left"
            />
          </div>
        </v-col>
        <v-col cols="10" class="pa-1">
          <v-text-field
            :model-value="String(property.value || '')"
            variant="outlined"
            density="compact"
            hide-details
            class="property-field"
          >
            <template v-slot:prepend-inner>
              <span class="property-prepend-inner">{{ property.name }}</span>
            </template>
          </v-text-field>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.flow-node {
  background: #2a2a2a !important;
  border: 2px solid #444 !important;
  border-radius: 8px;
  overflow: visible;
  user-select: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
}

.node-title {
  background: #3a3a3a;
  color: #fff;
  font-weight: 600;
  font-size: 14px;
  min-height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.port-row {
  min-height: 40px;
}

.port-container {
  display: flex;
  align-items: center;
  height: 24px;
  position: relative;
}

.port-input-container {
  justify-content: flex-start;
  /* padding-left: 8px; */
}

.port-output-container {
  justify-content: flex-end;
  /* padding-right: 8px; */
}

.port-handle {
  position: relative;
  padding: 20px;
}

.port-label {
  font-size: 15px;
  color: #ccc;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.property-row {
  min-height: 40px;
}

.property-handle {
  position: relative;
  margin-left: -8px;
}

.property-prepend-inner {
  color: #888;
}

.property-field {
  width: 100%;
}

:deep(.property-field input) {
  text-align: right;
}

/* Vue Flow specific styles */
:deep(.vue-flow__node) {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
}

:deep(.vue-flow__handle) {
  background: #666 !important;
  border: 0px !important;
  width: 14px !important;
  height: 14px !important;
}

:deep(.vue-flow__handle-left) {
  left: 8px !important;
  transform: translateY(-50%) !important;
}

:deep(.vue-flow__handle-right) {
  right: 8px !important;
  transform: translateY(-50%) !important;
}

:deep(.vue-flow__handle:hover) {
  background: #888 !important;
  transform: translateY(-50%) scale(1.2) !important;
}

:deep(.property-handle .vue-flow__handle) {
  background-color: #333 !important;
}

:deep(.property-handle .vue-flow__handle:hover) {
  background-color: #888 !important;
  transform: translateY(-50%) scale(1.2) !important;
}

:deep(.v-card) {
  background-color: #2a2a2a;
}

:deep(.v-card-title) {
  color: #fff;
}

:deep(.v-divider) {
  border-color: #444;
}

:deep(.v-text-field) {
  color: #fff;
}

:deep(.v-field__input) {
  color: #fff;
}

:deep(.v-field__label) {
  color: #aaa !important;
}

:deep(.v-field--focused .v-field__label) {
  color: #2196F3 !important;
}

:deep(.v-field__outline) {
  color: #555 !important;
}

:deep(.v-field--focused .v-field__outline) {
  color: #2196F3 !important;
}
</style>
