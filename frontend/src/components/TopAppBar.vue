<script setup lang="ts">
import { ref, watch } from 'vue'
import { workflowState, activeTabId } from '../stores/workflow'

const emit = defineEmits<{
  tabChanged: [name: string]
}>()

// Local state
const draggedTab = ref<string | null>(null)
const workflowTabs = ref([
  { id: 'tab1', name: 'untitled' }
])
let tabCounter = 1

// Methods
const getTabName = (tabId: string) => {
  const tab = workflowTabs.value.find(t => t.id === tabId)
  return tab?.name || 'untitled'
}

const addNewTab = () => {
  tabCounter++
  const newTab = {
    id: `tab${tabCounter}`,
    name: 'untitled'
  }
  workflowTabs.value.push(newTab)
  workflowState.setActiveTab(newTab.id, newTab.name)
}

const deleteTab = (tabId: string, event: MouseEvent) => {
  event.stopPropagation()

  // Can only delete the selected tab
  if (activeTabId.value !== tabId) {
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
          workflowState.setActiveTab(lastTab.id, lastTab.name)
        }
      } else {
        const nextTab = workflowTabs.value[index]
        if (nextTab) {
          workflowState.setActiveTab(nextTab.id, nextTab.name)
        }
      }
    }
  }
}

const handleTabSwitch = (newTabId: string, event?: MouseEvent) => {
  const tabName = getTabName(newTabId)
  workflowState.setActiveTab(newTabId, tabName)
}

const updateCurrentTabName = (name: string) => {
  const tab = workflowTabs.value.find(t => t.id === activeTabId.value)
  if (tab) {
    tab.name = name
    workflowState.updateActiveTabName(name)
  }
}

// Watch for active tab changes and emit event
watch(activeTabId, () => {
  emit('tabChanged', workflowState.activeTabName)
}, { immediate: true })

// Drag and drop handlers
const handleDragStart = (event: DragEvent, tabId: string) => {
  draggedTab.value = tabId
  event.dataTransfer?.setData('text/plain', tabId)
}

const handleDragOver = (event: DragEvent) => {
  event.preventDefault()
}

const handleDrop = (event: DragEvent, targetTabId: string) => {
  event.preventDefault()
  if (draggedTab.value && draggedTab.value !== targetTabId) {
    const draggedIndex = workflowTabs.value.findIndex(t => t.id === draggedTab.value)
    const targetIndex = workflowTabs.value.findIndex(t => t.id === targetTabId)

    if (draggedIndex !== -1 && targetIndex !== -1) {
      const [draggedItem] = workflowTabs.value.splice(draggedIndex, 1)
      if (draggedItem) {
        workflowTabs.value.splice(targetIndex, 0, draggedItem)
      }
    }
  }
  draggedTab.value = null
}

const handleDragEnd = () => {
  draggedTab.value = null
}

// Expose methods for parent
defineExpose({
  getActiveTabName: () => workflowState.activeTabName,
  addNewTab,
  updateCurrentTabName
})
</script>

<template>
  <v-app-bar elevation="1" class="top-bar">
    <!-- Left side: Title, Tabs, New Tab, Edit -->
    <div class="d-flex align-center flex-grow-1">
      <span class="text-h6 mr-8">ATTPC Flow</span>

      <!-- Workflow Tabs -->
      <div class="d-flex align-center">
        <v-tabs
          v-model="activeTabId"
          density="compact"
          hide-slider
          class="workflow-tabs"
        >
          <v-tab
            v-for="tab in workflowTabs"
            :key="tab.id"
            :value="tab.id"
            class="custom-tab"
            draggable="true"
            @click="handleTabSwitch(tab.id, $event)"
            @dragstart="handleDragStart($event, tab.id)"
            @dragover="handleDragOver"
            @drop="handleDrop($event, tab.id)"
            @dragend="handleDragEnd"
          >
            <div class="d-flex align-center ga-2">
              <span>{{ tab.name }}</span>
              <v-btn
                icon="mdi-close"
                variant="text"
                size="x-small"
                v-if="activeTabId === tab.id"
                @click="deleteTab(tab.id, $event)"
                class="ml-0.5 tab-delete-btn"
              ></v-btn>
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
        >
        </v-btn>
      </div>
    </div>

    <!-- Right side: Edit button -->
    <v-btn variant="text" size="small">
      <v-icon start>mdi-pencil-outline</v-icon>
      Edit
    </v-btn>
  </v-app-bar>
</template>

<style scoped>
.top-bar {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

/* Custom tab styles - responsive */
:deep(.custom-tab) {
  min-width: auto;
  padding: 0 1rem 0 1rem;
  text-transform: none;
  border-bottom: 2px solid transparent;
  transition: all 0.2s ease;
  cursor: pointer;
  position: relative;
  font-size: 1.0rem;
}

:deep(.custom-tab.v-tab--selected) {
  color: rgb(var(--v-theme-primary));
  border-bottom-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.08);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
  border-radius: 4px 4px 0 0;
  font-size: 1.0rem;
  font-weight: 500;
  padding-right: 0.25rem !important;
}

:deep(.custom-tab:hover) {
  background-color: rgba(var(--v-theme-surface-variant), 0.4);
}

:deep(.custom-tab.v-tab--selected:hover) {
  background-color: rgba(var(--v-theme-primary), 0.12);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  transform: translateY(-3px);
}

/* Tab delete button - always visible when tab is selected */
:deep(.tab-delete-btn) {
  opacity: 1;
  transition: opacity 0.2s ease;
}

:deep(.tab-delete-btn:hover) {
  color: #ff5252 !important;
  background-color: rgba(255, 82, 82, 0.1) !important;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  :deep(.custom-tab) {
    padding: 0 0.125rem 0 0.75rem;
  }
}

@media (max-width: 480px) {
  /* Hide title on small screens */
  .text-h6.mr-8 {
    display: none;
  }

  /* Adjust tab spacing */
  :deep(.custom-tab) {
    padding: 0 0.125rem 0 0.5rem;
    font-size: 0.875rem;
  }
}
</style>
