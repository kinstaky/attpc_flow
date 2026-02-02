<script setup lang="ts">
import { ref, computed, inject } from 'vue'
import {
  tabs,
  setActiveTab,
  activeTabName,
  activeTabId,
  isTabSaved,
  closeActiveTab,
  createTab
} from '../models/tabs'
import { createWorkflow, workflowNameExists } from '../api/workflow'
import { Workflow } from '../models/workflow'

// Inject error handler from parent
const showError = inject<(message: string) => void>('showError', (msg: string) => {
  console.error('Error (no handler):', msg)
})

// Drag and drop state
const draggedTab = ref<string | null>(null)

// Dialog state
const nameDialogInput = ref('')
const showSaveDialog = ref(false)
const showNameDialog = ref(false)

// Writable computed for v-tabs v-model
const activeTabModel = computed({
  get: () => activeTabId.value,
  set: (value: string) => {
    // Ensure the tab exists before setting it as active
    if (tabs.value.some(tab => tab.id === value)) {
      setActiveTab(value)
    }
  }
})

// Name dialog handlers
const handleNameDialogConfirm = async () => {
  const workflowName = nameDialogInput.value.trim()
  if (!workflowName) return

  try {
    // Check if workflow already exists
    const exists = await workflowNameExists(workflowName)

    if (exists) {
      // Workflow exists, just open it
      createTab(workflowName)
    } else {
      // Workflow doesn't exist - create a new one
      const newWorkflow = new Workflow(workflowName)
      await createWorkflow(newWorkflow)
      await createTab(workflowName)
    }
    // Close the dialog and clear input
    showNameDialog.value = false
    nameDialogInput.value = ''
  } catch (error) {
    showError(`Failed to open workflow "${workflowName}": ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

const handleNameDialogCancel = () => {
  showNameDialog.value = false
}

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
    // Get current tabs array
    const currentTabs = [...tabs.value]
    const draggedIndex = currentTabs.findIndex(t => t.id === draggedTab.value)
    const targetIndex = currentTabs.findIndex(t => t.id === targetTabId)

    if (draggedIndex !== -1 && targetIndex !== -1) {
      // Remove dragged tab and insert at new position
      const [draggedItem] = currentTabs.splice(draggedIndex, 1)
      if (draggedItem) {
        currentTabs.splice(targetIndex, 0, draggedItem)

        // Update the tabs array in the store
        // Since tabs is a reactive array, we need to modify it directly
        tabs.value.splice(0, tabs.value.length, ...currentTabs)
      }
    }
  }
  draggedTab.value = null
}

const handleDragEnd = () => {
  draggedTab.value = null
}
</script>

<template>
  <v-app-bar elevation="1" class="top-bar">
    <!-- Left side: Title, Tabs, New Tab, Edit -->
    <div class="d-flex align-center flex-grow-1">
      <span class="text-h6 mr-8">ATTPC Flow</span>

      <!-- Workflow Tabs -->
      <div class="d-flex align-center">
        <v-tabs
          v-model="activeTabModel"
          density="compact"
          hide-slider
          class="workflow-tabs"
        >
          <v-tab
            v-for="tab in tabs"
            :key="tab.id"
            :value="tab.id"
            class="custom-tab"
            draggable="true"
            @click="setActiveTab(tab.id)"
            @dragstart="handleDragStart($event, tab.id)"
            @dragover="handleDragOver"
            @drop="handleDrop($event, tab.id)"
            @dragend="handleDragEnd"
          >
            <div class="d-flex align-center ga-2">
              <span>{{ activeTabName }}</span>
              <span
                v-if="!isTabSaved(tab.id)"
                class="unsaved-indicator"
                title="Not saved to file"
              >•</span>
              <v-btn
                icon="mdi-close"
                variant="text"
                size="x-small"
                v-if="activeTabId === tab.id"
                @click="showSaveDialog = true"
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
          @click="showNameDialog = true"
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

  <!-- Save Tab Dialog -->
  <v-dialog v-model="showSaveDialog" max-width="400" persistent>
    <v-card>
      <v-card-title>Save workflow</v-card-title>
      <v-card-text>
        <p>Would you like to save current workflow?</p>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn @click="showSaveDialog = false">Cancel</v-btn>
        <v-btn @click="closeActiveTab(false)">Don't Save</v-btn>
        <v-btn color="primary" @click="closeActiveTab(true)">Save</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Name Dialog for Unnamed Workflow -->
  <v-dialog v-model="showNameDialog" max-width="400" persistent>
    <v-card>
      <v-card-title>Name Workflow</v-card-title>
      <v-card-text>
        <p class="mb-4">Please enter a name for this workflow:</p>
        <v-text-field
          v-model="nameDialogInput"
          label="Workflow Name"
          variant="outlined"
          density="compact"
          autofocus
          @keyup.enter="handleNameDialogConfirm"
          @keyup.escape="handleNameDialogCancel"
        ></v-text-field>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn @click="handleNameDialogCancel">Cancel</v-btn>
        <v-btn
          color="primary"
          @click="handleNameDialogConfirm"
          :disabled="!nameDialogInput.trim()"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
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

/* Unsaved tab indicator */
.unsaved-indicator {
  color: #ff9800;
  font-size: 1.2rem;
  margin-left: 4px;
  opacity: 0.8;
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
