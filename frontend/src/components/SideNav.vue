<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useTheme } from 'vuetify'

const theme = useTheme()
const isDark = ref(true)
const showNodesPanel = ref(false)
const showWorkflowsPanel = ref(false)
const nodeCategories = ref<Record<string, string[]>>({})
const workflows = ref<string[]>([])

const toggleTheme = () => {
  isDark.value = !isDark.value
  theme.global.name.value = isDark.value ? 'dark' : 'light'
}

const openNodesLibrary = () => {
  showNodesPanel.value = !showNodesPanel.value
  showWorkflowsPanel.value = false
  console.log('Toggle nodes library panel')
}

const openWorkflows = () => {
  showWorkflowsPanel.value = !showWorkflowsPanel.value
  showNodesPanel.value = false
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
    const response = await fetch('/workflows')
    if (response.ok) {
      workflows.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to fetch workflows:', error)
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
      <!-- Top section with icon buttons -->
      <div class="pa-2">
        <v-btn
          icon
          variant="text"
          size="default"
          class="mb-2"
          @click="openNodesLibrary"
        >
          <v-icon>mdi-shape-outline</v-icon>
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

      <!-- Bottom section with controls -->
      <div class="pa-2">
        <v-btn
          icon
          variant="text"
          size="default"
          class="mb-2"
          @click="toggleTheme"
        >
          <v-icon>{{ isDark ? 'mdi-brightness-4' : 'mdi-brightness-6' }}</v-icon>
          <v-tooltip activator="parent" location="end">
            {{ isDark ? 'Switch to Light' : 'Switch to Dark' }}
          </v-tooltip>
        </v-btn>

        <v-btn
          icon
          variant="text"
          size="default"
          @click="openSettings"
        >
          <v-icon>mdi-cog</v-icon>
          <v-tooltip activator="parent" location="end">Settings</v-tooltip>
        </v-btn>
      </div>
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
      <span class="text-h6 pl-4">Nodes</span>
      <v-spacer></v-spacer>
      <v-btn icon variant="text" @click="showNodesPanel = false">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-toolbar>

    <div class="pa-3">
      <v-expansion-panels variant="accordion" multiple>
        <v-expansion-panel v-for="(nodes, category) in nodeCategories" :key="category as string">
          <v-expansion-panel-title>
            {{ category }}
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <div class="d-flex flex-column ga-2">
              <v-chip
                v-for="node in nodes"
                :key="node"
                size="small"
                variant="outlined"
                class="justify-start"
                draggable
              >
                {{ node }}
              </v-chip>
            </div>
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
      <v-btn icon variant="text" @click="showWorkflowsPanel = false">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-toolbar>

    <div class="pa-3">
      <v-list density="compact" nav>
        <v-list-item v-for="workflow in workflows" :key="workflow">
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
</style>
