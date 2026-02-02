<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { Node, interfaceColor, interfaceHoverColor, basicType, isArrayType, InterfaceType } from '../types/node'

interface Linking {
  active: boolean,
  node: number,
  portIndex: number,
  portType: string,
  dataType: InterfaceType
}

interface Props {
  nodeData: Node
  linking: Linking
  selected: boolean
}

const props = defineProps<Props>()

// Constants for node layout
const nodeWidth = 360

// Get max number of ports to align rows
const maxPorts = computed(
  () => Math.max(props.nodeData.inputs.length, props.nodeData.outputs.length)
)

const linkable = (nodeId: number, portType: string, dataType: InterfaceType) => {
  if (!props.linking.active) return false
  if (nodeId == props.linking.node) return false
  if (props.linking.portType == "input") {
    if (portType != "output") return false
    if (dataType != props.linking.dataType) return false
    return true
  } else if (props.linking.portType == "output") {
    if (portType == "output") return false
    if (dataType != props.linking.dataType) return false
    return true
  } else if (props.linking.portType == "property") {
    if (portType != "output") return false
    if (dataType != props.linking.dataType) return false
    return true
  }
  return false
}

const isHandleSelf = (nodeId: number, portType: string, portIndex: number) => {
  return props.linking.portType == portType
    && props.linking.node == nodeId
    && props.linking.portIndex == portIndex
}

const isInputSelf = (nodeId: number, portIndex: number) => {
  return isHandleSelf(nodeId, "input", portIndex)
}

const isOutputSelf = (nodeId: number, portIndex: number) => {
  return isHandleSelf(nodeId, "output", portIndex)
}

const isPropertySelf = (nodeId: number, portIndex: number) => {
  return isHandleSelf(nodeId, "property", portIndex)
}

</script>

<template>
  <v-card class="flow-node" :class="{ 'flow-node--selected': selected }" :style="{ width: nodeWidth + 'px' }" elevation="2">
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
                :class="[
                  props.linking.active
                    && !linkable(nodeData.id, 'input', nodeData.inputs[index-1]?.type)
                    && !isInputSelf(nodeData.id, index-1)
                    ? 'handle-hidden' : '',
                  `handle-${basicType(nodeData.inputs[index - 1]?.type)}`,
                  isArrayType(nodeData.inputs[index - 1]?.type) ? 'handle-array' : '',
                ]"
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
                  :class="[
                    props.linking.active
                      && !linkable(nodeData.id, 'output', nodeData.outputs[index-1]?.type)
                      && !isOutputSelf(nodeData.id, index-1)
                      ? 'handle-hidden' : '',
                    `handle-${basicType(nodeData.outputs[index-1]?.type)}`,
                    isArrayType(nodeData.outputs[index-1]?.type) ? 'handle-array' : '',
                  ]"
                />
              </div>
          </div>
        </v-col>
        <v-col cols="5" v-else class="pa-1"></v-col>
      </v-row>
      <!-- Properties (Full line) -->
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
              :id="`property-${index}`"
              type="target"
              :position="Position.Left"
              :class="[
                props.linking.active ?
                  linkable(nodeData.id, 'property', property.type)
                    || isPropertySelf(nodeData.id, index)
                    ? '' : 'handle-hidden'
                  : property.links.length > 0 ? '' : 'handle-unlinked',
                `handle-${basicType(property.type)}`,
                isArrayType(property.type) ? 'handle-array' : '',
              ]"
            />
          </div>
        </v-col>
        <v-col cols="10" class="pa-1">
          <v-text-field
            v-model="property.value"
            variant="outlined"
            density="compact"
            hide-details
            class="property-field"
            :disabled="property.links.length > 0"
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
  /* cursor: pointer; */
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

:deep(.vue-flow__node.selected .flow-node),
.flow-node--selected {
  border-color: rgb(var(--v-theme-primary)) !important;
  box-shadow: 0 0 0 2px rgba(var(--v-theme-primary), 0.35), 0 6px 14px rgba(0, 0, 0, 0.4) !important;
}

:deep(.vue-flow__node.selected .node-title),
.flow-node--selected .node-title {
  background: rgba(var(--v-theme-primary), 0.2);
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
}

.port-output-container {
  justify-content: flex-end;
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

:deep(.property-field .v-field--variant-outlined .v-field__outline) {
  color: #eee !important;
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

/* Type-based handle colors */
:deep(.handle-int) {
  background: v-bind('interfaceColor["int"]') !important; /* Green */
}

:deep(.handle-str) {
  background: v-bind('interfaceColor["str"]') !important; /* Blue */
}

:deep(.handle-float) {
  background: v-bind('interfaceColor["float"]') !important; /* Orange */
}

:deep(.handle-bool) {
  background: v-bind('interfaceColor["bool"]') !important; /* Purple */
}

:deep(.vue-flow__handle:hover) {
  transform: translateY(-50%) scale(1.2) !important;
}

/* Array shape transformation */
:deep(.handle-array) {
  border-radius: 0% !important; /* Square for arrays */
  transform: translateY(-50%) rotate(45deg) !important; /* Diamond shape */
}

/* Hover states for type-based handles  */
:deep(.handle-int:hover) {
  background: v-bind('interfaceHoverColor["int"]') !important;
}

:deep(.handle-str:hover) {
  background: v-bind('interfaceHoverColor["str"]') !important;
}

:deep(.handle-float:hover) {
  background: v-bind('interfaceHoverColor["float"]') !important;
}

:deep(.handle-bool:hover) {
  background: v-bind('interfaceHoverColor["bool"]') !important;
}

/* Array hover states - maintain diamond shape with scaling */
:deep(.handle-array:hover) {
  transform: translateY(-50%) rotate(45deg) scale(1.2) !important;
}

:deep(.handle-unlinked) {
  background: #333 !important;
}

:deep(.handle-hidden) {
  opacity: 0 !important;
}

:deep(.handle-unlinked.handle-int:hover) {
  background: v-bind('interfaceHoverColor["int"]') !important;
}

:deep(.handle-unlinked.handle-float:hover) {
  background: v-bind('interfaceHoverColor["float"]') !important;
}

:deep(.handle-unlinked.handle-bool:hover) {
  background: v-bind('interfaceHoverColor["bool"]') !important;
}

:deep(.handle-unlinked.handle-str:hover) {
  background: v-bind('interfaceHoverColor["str"]') !important;
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
