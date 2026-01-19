<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted } from 'vue'

const activeTab = ref('tab1')
const workspaceInput = ref('')
const editingTabId = ref<string | null>(null)
const editingTabName = ref('')

const workflowTabs = ref([
  { id: 'tab1', name: 'Tab1' },
])

let tabCounter = 1

const addNewTab = () => {
  tabCounter++
  const newTabId = `tab${Date.now()}`
  workflowTabs.value.push({
    id: newTabId,
    name: `Tab${tabCounter}`
  })
  activeTab.value = newTabId
}

const startEditTab = (tabId: string, currentName: string) => {
  editingTabId.value = tabId
  editingTabName.value = currentName
}

const finishEditTab = () => {
  if (editingTabId.value && editingTabName.value.trim()) {
    const tab = workflowTabs.value.find(t => t.id === editingTabId.value)
    if (tab) {
      tab.name = editingTabName.value.trim()
    }
  }
  editingTabId.value = null
  editingTabName.value = ''
}

const cancelEditTab = () => {
  editingTabId.value = null
  editingTabName.value = ''
}

const deleteTab = (tabId: string, event: MouseEvent) => {
  event.stopPropagation()

  // Can only delete the selected tab
  if (activeTab.value !== tabId) {
    return
  }

  if (workflowTabs.value.length > 1) {
    const index = workflowTabs.value.findIndex(t => t.id === tabId)
    if (index !== -1) {
      workflowTabs.value.splice(index, 1)
      // Select adjacent tab
      if (index >= workflowTabs.value.length) {
        const lastTab = workflowTabs.value[workflowTabs.value.length - 1]
        if (lastTab) {
          activeTab.value = lastTab.id
        }
      } else {
        const nextTab = workflowTabs.value[index]
        if (nextTab) {
          activeTab.value = nextTab.id
        }
      }
    }
  }
}

const handleTabKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter') {
    finishEditTab()
  } else if (event.key === 'Escape') {
    cancelEditTab()
  } else if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].indexOf(event.key) !== -1) {
    // Allow arrow keys and navigation keys to work normally
    event.stopPropagation()
  }
}

const handleTabSwitch = (newTabId: string, event?: MouseEvent) => {
  // If we're editing, don't switch tabs (unless it's a click)
  if (editingTabId.value && !event) {
    return
  }

  // If we're editing and this is a click, finish the edit first
  if (editingTabId.value && event) {
    finishEditTab()
  }
  activeTab.value = newTabId
}

const handleGlobalClick = (event: MouseEvent) => {
  // Check if we're editing and if the click is outside the input
  if (editingTabId.value) {
    const target = event.target as HTMLElement
    if (!target.closest('.tab-edit-input')) {
      finishEditTab()
    }
  }
}

onMounted(() => {
  document.addEventListener('click', handleGlobalClick)
})

onUnmounted(() => {
  document.removeEventListener('click', handleGlobalClick)
})
</script>

<template>
  <v-app-bar elevation="0" height="48" class="top-bar">
    <!-- Left side items -->
    <div class="d-flex align-center ga-4">
      <span class="text-h6 font-weight-bold">ATTPC Flow</span>

      <v-btn variant="text" size="small" class="text-none">
        <span class="ml-1">Workflow</span>
      </v-btn>

      <v-btn variant="text" size="small" class="text-none">
        <span class="ml-1">Edit</span>
      </v-btn>

      <v-btn variant="text" size="small" class="text-none">
        <span class="ml-1">Help</span>
      </v-btn>

      <v-divider vertical class="mx-2"></v-divider>

      <!-- Workflow Tabs -->
      <div class="d-flex align-center">
        <v-tabs :model-value="activeTab" height="32" color="primary" class="custom-tabs">
          <v-tab
            v-for="tab in workflowTabs"
            :key="tab.id"
            :value="tab.id"
            class="custom-tab"
            @click="handleTabSwitch(tab.id, $event)"
          >
            <div v-if="editingTabId === tab.id" class="d-flex align-center ga-1">
              <input
                ref="editInput"
                v-model="editingTabName"
                @blur="finishEditTab"
                @keydown="handleTabKeydown"
                @click.stop
                class="tab-edit-input"
                style="width: 100px; font-size: 14px;"
              >
            </div>
            <div v-else class="d-flex align-center ga-2" @dblclick="startEditTab(tab.id, tab.name)">
              <span>{{ tab.name }}</span>
              <v-btn
                v-if="activeTab === tab.id"
                icon="mdi-close"
                size="x-small"
                variant="text"
                class="tab-delete-btn"
                @click="deleteTab(tab.id, $event)"
              >
              </v-btn>
            </div>
          </v-tab>
        </v-tabs>

        <!-- Add new tab button -->
        <v-btn
          icon="mdi-plus"
          size="small"
          variant="text"
          class="ml-2"
          @click="addNewTab"
        ></v-btn>
      </div>
    </div>

    <!-- Right side items -->
    <v-spacer></v-spacer>

    <div class="d-flex align-center ga-2">
      <v-text-field
        v-model="workspaceInput"
        placeholder="Workspace..."
        density="compact"
        variant="outlined"
        hide-details
        style="width: 200px"
      ></v-text-field>

      <v-btn variant="flat" color="primary" size="small">
        <v-icon start>mdi-play</v-icon>
        Run
      </v-btn>

      <v-btn icon size="small" variant="text">
        <v-icon>mdi-menu</v-icon>
      </v-btn>
    </div>
  </v-app-bar>
</template>

<style scoped>
.top-bar {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

/* Custom tab styles */
:deep(.custom-tabs .v-tab) {
  min-width: auto;
  padding: 0 4px 0 16px;
  text-transform: none;
  border-bottom: 2px solid transparent;
  transition: all 0.2s ease;
}

:deep(.custom-tabs .v-tab.v-tab--selected) {
  color: rgb(var(--v-theme-primary));
  border-bottom-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.08);
}

:deep(.custom-tabs .v-tab:hover) {
  background-color: rgba(var(--v-theme-surface-variant), 0.4);
}

/* Tab delete button - always visible when tab is selected */
.tab-delete-btn {
  opacity: 1;
  transition: opacity 0.2s ease;
}

.tab-delete-btn:hover {
  color: #ff5252 !important;
  background-color: rgba(255, 82, 82, 0.1) !important;
}

/* Tab edit input */
.tab-edit-input {
  background: transparent;
  border: 1px solid rgb(var(--v-theme-primary));
  border-radius: 4px;
  padding: 2px 8px;
  color: inherit;
  outline: none;
}

.tab-edit-input:focus {
  background: rgba(var(--v-theme-surface), 0.8);
}
</style>
