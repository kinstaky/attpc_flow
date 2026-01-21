<script setup lang="ts">
import { ref, onMounted, inject } from 'vue'
import { useTheme } from 'vuetify'
import {
  addNewTab,
  saveTab,
  updateActiveTabName,
  activeTabId,
  activeTabName,
  isTabAttached,
  activeWorkflow,
  updateActiveWorkflow
} from '../stores/tabs'
import { getWorkflow, listWorkflows } from '../services/workflow'

// Inject error handler from parent
const showError = inject<(message: string) => void>('showError', (msg: string) => {
  console.error('Error (no handler):', msg)
})

const theme = useTheme()
const isDark = ref(true)
const showNodesPanel = ref(false)
const showWorkflowsPanel = ref(false)
const showMenu = ref(false)
const nodeCategories = ref<Record<string, string[]>>({})
const workflows = ref<string[]>([])

const toggleTheme = () => {
  isDark.value = !isDark.value
  theme.global.name.value = isDark.value ? 'dark' : 'light'
}

const openNodesLibrary = async () => {
  showNodesPanel.value = !showNodesPanel.value
  showWorkflowsPanel.value = false

  // Always refresh nodes when opening the panel
  if (showNodesPanel.value) {
    await fetchNodes()
  }

  console.log('Toggle nodes library panel')
}

const openWorkflows = async () => {
  showWorkflowsPanel.value = !showWorkflowsPanel.value
  showNodesPanel.value = false

  // Always refresh workflows when opening the panel
  if (showWorkflowsPanel.value) {
    await fetchWorkflows()
  }

  console.log('Toggle workflows panel')
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

const fetchWorkflows = async () => {
  try {
    workflows.value = await listWorkflows()
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to fetch workflows'
    showError(errorMessage)
    console.error('Failed to fetch workflows:', error)
  }
}

const openWorkflow = async (workflowName: string) => {
  try {
    // Check if active tab is empty (null name, unattached)
    const currentTabId = activeTabId.value
    const currentTabName = activeTabName.value
    const isAttachedTab = isTabAttached(currentTabId)
    const currentWorkflow = activeWorkflow.value ?? null

    let targetTabId: string

    if (!currentTabName && !isAttachedTab) {
      // Reuse the empty active tab
      targetTabId = currentTabId
    } else {
      // Create a new tab
      addNewTab()
      targetTabId = activeTabId.value
    }

    // Set the tab name to match the workflow
    // updateActiveTabName(workflowName)

    // Get workflow data from server
    const workflowData = await getWorkflow(workflowName)
    updateActiveWorkflow(workflowData)

    // Mark the tab as attached (saved)
    saveTab(targetTabId)

    console.log('Opened workflow:', workflowName, 'in tab:', targetTabId)
    // console.log('Workflow data:', workflowData)

    // Close the workflows submenu
    showWorkflowsPanel.value = false
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to open workflow'
    showError(errorMessage)
    console.error('Failed to open workflow:', error)
  }
}

onMounted(() => {
  fetchNodes()
  fetchWorkflows()
})
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
      <v-btn icon variant="text" @click="showNodesPanel = false">
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
                @click="() => {}"
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
      <v-btn icon variant="text" @click="showWorkflowsPanel = false">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-toolbar>

    <div class="pa-3">
      <v-list density="compact" nav>
        <v-list-item
          v-for="workflow in workflows"
          :key="workflow"
          @click="openWorkflow(workflow)"
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
}

@media (max-width: 480px) {
  :deep(.nodes-panel),
  :deep(.workflows-panel) {
    width: 100vw !important;
    left: 48px !important;
  }
}
</style>
