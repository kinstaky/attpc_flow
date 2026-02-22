<script setup lang="ts">
import { ref, inject, computed } from 'vue'
import { useTheme } from 'vuetify'
import {
  activeWorkflowAddNode,
  createTab,
  activeWorkspace,
} from '../models/tabs'
import { listWorkflows } from '../api/workflow'
import ExecutionProgressPanel from './ExecutionProgressPanel.vue'
import { parseNode } from '../types/node'

// Inject error handler from parent
const showError = inject<(message: string) => void>('showError', (msg: string) => {
  console.error('Error (no handler):', msg)
})

const theme = useTheme()
const isDark = ref(true)
const showPanel = ref("")

// Helper function to create panel computed properties
const createPanelComputed = (panelType: string) => computed({
  get: () => showPanel.value === panelType,
  set: (val) => showPanel.value = val ? panelType : ""
})

const showNodesPanel = createPanelComputed("nodes")
const showWorkflowsPanel = createPanelComputed("workflows")
const showProgressPanel = createPanelComputed("progress")
const showMenu = ref(false)
const nodeCategories = ref<Record<string, string[]>>({})
const workflows = ref<string[]>([])

const toggleTheme = () => {
  isDark.value = !isDark.value
  theme.global.name.value = isDark.value ? 'dark' : 'light'
}

// Generic panel opener with optional refresh
const openPanel = async (
  panelType: 'nodes' | 'workflows' | 'progress',
  refreshFn?: () => Promise<void>
) => {
  showPanel.value = showPanel.value === panelType ? "" : panelType

  // Always refresh data when opening the panel
  if (showPanel.value === panelType && refreshFn) {
    await refreshFn()
  }
}

const openNodesLibrary = async () => {
  await openPanel('nodes', fetchNodes)
}

const openWorkflows = async () => {
  await openPanel('workflows', fetchWorkflows)
}

const openProgress = async () => {
  await openPanel('progress') // No refresh needed - component handles it
}

const openSettings = () => {
  // Placeholder for settings
  console.log('Open settings')
}

// Fetch data from server
const fetchNodes = async () => {
  try {
    const response = await fetch('/nodes')
    if (response.ok) {
      nodeCategories.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to fetch nodes:', error)
  }
}

const addNode = async (nodeName: string) => {
  try {
    const response = await fetch(`/nodes/${nodeName}`)
    if (response.ok) {
      const nodeData = await response.json()
      let position = { x: 400 + Math.random() * 100, y: 200 + Math.random() * 100 }
     const newNode = parseNode(nodeData, position)
      activeWorkflowAddNode(newNode)
    }
  } catch (error) {
    console.error(`Failed to fetch node ${nodeName}:`, error)
  }
}


const fetchWorkflows = async () => {
  try {
    workflows.value = await listWorkflows()
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to fetch workflows'
    showError(errorMessage)
    console.error('Failed to fetch workflows:', error)
  }
}
</script>

<template>
  <v-navigation-drawer
    permanent
    width="56"
    color="surface"
    class="side-nav"
  >
    <div class="d-flex flex-column h-100">
      <!-- Top buttons -->
      <div class="d-flex flex-column ga-2 pa-2">
        <!-- Menu button -->
        <v-menu v-model="showMenu" :close-on-content-click="false">
          <template v-slot:activator="{ props }">
            <v-btn
              icon
              variant="text"
              size="default"
              v-bind="props"
            >
              <v-icon>mdi-menu</v-icon>
              <v-tooltip activator="parent" location="end">Menu</v-tooltip>
            </v-btn>
          </template>
          <v-list density="compact" nav>
            <v-list-item @click="toggleTheme">
              <template v-slot:prepend>
                <v-icon>{{ isDark ? 'mdi-brightness-4' : 'mdi-brightness-6' }}</v-icon>
              </template>
              <v-list-item-title>Theme</v-list-item-title>
            </v-list-item>
            <v-list-item>
              <template v-slot:prepend>
                <v-icon>mdi-help-circle-outline</v-icon>
              </template>
              <v-list-item-title>Help</v-list-item-title>
            </v-list-item>
            <v-list-item>
              <template v-slot:prepend>
                <v-icon>mdi-information-outline</v-icon>
              </template>
              <v-list-item-title>About</v-list-item-title>
            </v-list-item>
            <v-list-item @click="openSettings">
              <template v-slot:prepend>
                <v-icon>mdi-cog</v-icon>
              </template>
              <v-list-item-title>Settings</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>

        <v-btn
          icon
          variant="text"
          size="default"
          class="mb-2"
          @click="openNodesLibrary"
        >
          <v-icon>mdi-transit-connection-variant</v-icon>
          <v-tooltip activator="parent" location="end">Nodes</v-tooltip>
        </v-btn>

        <v-btn
          icon
          variant="text"
          size="default"
          @click="openWorkflows"
        >
          <v-icon>mdi-folder-open-outline</v-icon>
          <v-tooltip activator="parent" location="end">Workflows</v-tooltip>
        </v-btn>

        <v-btn
          icon
          variant="text"
          size="default"
          @click="openProgress"
        >
          <v-icon>mdi-list-status</v-icon>
          <v-tooltip activator="parent" location="end">Progress</v-tooltip>
        </v-btn>
      </div>

      <v-spacer></v-spacer>
    </div>
  </v-navigation-drawer>

  <!-- Nodes Library Panel -->
  <v-navigation-drawer
    v-model="showNodesPanel"
    temporary
    width="280"
    location="left"
    class="nodes-panel"
  >
    <v-toolbar flat>
      <span class="text-h5 pl-4">Nodes</span>
      <v-spacer></v-spacer>
      <v-btn
        icon
        variant="text"
        @click="fetchNodes"
        title="Refresh nodes"
      >
        <v-icon>mdi-refresh</v-icon>
      </v-btn>
      <v-btn icon variant="text" @click="showPanel = ''">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-toolbar>

    <div class="pa-2">
      <v-expansion-panels variant="accordion" multiple>
        <v-expansion-panel v-for="(nodes, category) in nodeCategories" :key="category as string">
          <v-expansion-panel-title class="text-subtitle-1">
            {{ category }}
          </v-expansion-panel-title>
          <v-expansion-panel-text class="pa-0">
            <v-list density="compact" nav>
              <v-list-item
                v-for="node in nodes"
                :key="node"
                @click="addNode(node)"
                class="node-item"
                draggable
              >
                <template v-slot:prepend>
                  <div class="node-dot"></div>
                </template>
                <v-list-item-title class="text-body-2">{{ node }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </div>
  </v-navigation-drawer>

  <!-- Workflows Panel -->
  <v-navigation-drawer
    v-model="showWorkflowsPanel"
    temporary
    width="280"
    location="left"
    class="workflows-panel"
  >
    <v-toolbar flat>
      <span class="text-h6 pl-4">Workflows</span>
      <v-spacer></v-spacer>
      <v-btn
        icon
        variant="text"
        @click="fetchWorkflows"
        title="Refresh workflows"
      >
        <v-icon>mdi-refresh</v-icon>
      </v-btn>
      <v-btn icon variant="text" @click="showPanel = ''">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-toolbar>

    <div class="pa-3">
      <v-list density="compact" nav>
        <v-list-item
          v-for="workflow in workflows"
          :key="workflow"
          @click="createTab(workflow)"
          class="workflow-item"
        >
          <template v-slot:prepend>
            <v-icon>mdi-file-outline</v-icon>
          </template>
          <v-list-item-title>{{ workflow }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </div>
  </v-navigation-drawer>

  <!-- Progress Panel -->
  <ExecutionProgressPanel
    v-model:visible="showProgressPanel"
    :workspace="activeWorkspace || undefined"
  />
</template>

<style scoped>
.side-nav {
  border-right: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

/* Position the panels to the right of the side nav */
:deep(.nodes-panel),
:deep(.workflows-panel) {
  left: 56px !important;
}

/* Workflow items hover effect */
.workflow-item {
  cursor: pointer;
}

.workflow-item:hover {
  background-color: rgba(var(--v-theme-surface-variant), 0.12);
}

/* Node items styling */
.node-item {
  cursor: pointer;
  min-height: 36px;
}

.node-item:hover {
  background-color: rgba(var(--v-theme-surface-variant), 0.12);
}

/* Solid fill circle for nodes - larger size */
.node-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: rgb(var(--v-theme-primary));
  margin-right: 12px;
  flex-shrink: 0;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  :deep(.nodes-panel),
  :deep(.workflows-panel) {
    width: 240px !important;
  }
  :deep(.status-panel) {
    width: 400px !important;
  }
}

@media (max-width: 480px) {
  :deep(.nodes-panel),
  :deep(.workflows-panel),
  :deep(.status-panel) {
    width: 100vw !important;
    left: 48px !important;
  }
}
</style>
