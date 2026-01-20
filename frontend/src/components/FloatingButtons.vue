<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { activeTabName, activeTabId, isTabAttached, getOtherTabNames, addNewTab, updateActiveTabName, attachTab } from '../stores/tabs'

// API base URL
const API_BASE = ''

// Local state
const showWorkflowMenu = ref(false)
const isRenaming = ref(false)
const renameInput = ref<HTMLInputElement>()
const currentWorkflow = ref(activeTabName.value || '')
const workspaceName = ref('Workspace 1')
const renameError = ref('')
const existingWorkflows = ref<string[]>([])
const otherTabNames = ref<string[]>([])

// Dialog state for save
const showNameDialog = ref(false)
const dialogTitle = ref('')
const dialogMessage = ref('')
const nameDialogInput = ref('')
const hasDialogError = ref(false)

// Update workflow name when store changes
watch(activeTabName, (newName) => {
  currentWorkflow.value = newName || ''
})

// Computed
const workflowDisplayName = computed(() => activeTabName.value || 'untitled')

// Workflow functions
const duplicateWorkflow = () => {
  addNewTab()
  showWorkflowMenu.value = false
}

const saveWorkflow = async () => {
  const workflowName = currentWorkflow.value?.trim()
  const currentTabId = activeTabId.value
  const isAttached = isTabAttached(currentTabId)
  
  if (isAttached) {
    // Attached tab: just update
    if (workflowName) {
      await updateWorkflow(workflowName)
    }
  } else {
    console.log("workflowName before input", workflowName)
    // Unattached tab
    if (!workflowName) {
      // Show dialog to enter workflow name
      dialogTitle.value = 'Save Workflow'
      dialogMessage.value = 'Please enter a name for this workflow:'
      nameDialogInput.value = ''
      hasDialogError.value = false
      showNameDialog.value = true
      return
    }
    console.log("workflowName after input", workflowName)
    // Check if name already exists
    try {
      const response = await fetch(`${API_BASE}/workflows`)
      if (response.ok) {
        const existingWorkflows = await response.json()
        if (existingWorkflows.indexOf(workflowName) !== -1) {
          // Name already exists, show dialog with current name
          dialogTitle.value = 'Rename Workflow'
          dialogMessage.value = `A workflow named "${workflowName}" already exists. Please choose a different name:`
          nameDialogInput.value = workflowName
          hasDialogError.value = true
          showNameDialog.value = true
          return
        }
      }
      // Name doesn't exist, proceed with save
      await createWorkflow(workflowName)
      attachTab(currentTabId)
    } catch (error) {
      console.error('Failed to check existing workflows:', error)
      // If we can't check, proceed with save
      await createWorkflow(workflowName)
      attachTab(currentTabId)
    }
  }
  
  showWorkflowMenu.value = false
}

const saveAsWorkflow = () => {
  console.log('SaveAs: TODO - not implemented yet')
  showWorkflowMenu.value = false
}

const renameWorkflow = async () => {
  isRenaming.value = true
  showWorkflowMenu.value = false
  renameError.value = ''

  // Fetch existing workflows for validation
  try {
    const response = fetch(`${API_BASE}/workflows`)
    if ((await response).ok) {
      existingWorkflows.value = await (await response).json()
    }
  } catch (error) {
    console.error('Failed to fetch workflows:', error)
  }

  // Get other tab names directly from store for validation
  otherTabNames.value = getOtherTabNames()

  nextTick(() => {
    renameInput.value?.focus()
    renameInput.value?.select()
  })
}

const validateAndFinishRename = async () => {
  const newName = currentWorkflow.value?.trim()

  // Skip if name hasn't changed
  if (newName === (activeTabName.value || '')) {
    isRenaming.value = false
    renameError.value = ''
    return
  }

  // Validate empty name
  if (!newName) {
    renameError.value = 'Name cannot be empty'
    return
  }

  const isAttached = isTabAttached(activeTabId.value)

  if (isAttached) {
    // Check against existing workflow files
    if (existingWorkflows.value.indexOf(newName) !== -1) {
      renameError.value = 'A workflow with this name already exists'
      return
    }
    // For attached tabs, create new and delete old via API
    await handleRenameAttached(activeTabName.value || '', newName)
    isRenaming.value = false
    renameError.value = ''
  } else {
    // Check against other tab names
    if (otherTabNames.value.indexOf(newName) !== -1) {
      renameError.value = 'Another tab already has this name'
      return
    }
    // Valid - update name directly
    updateActiveTabName(newName)
    isRenaming.value = false
    renameError.value = ''
  }
}

const cancelRename = () => {
  isRenaming.value = false
  renameError.value = ''
  currentWorkflow.value = activeTabName.value || ''
}

// Handle rename for attached tabs - create new workflow and delete old one
const handleRenameAttached = async (oldName: string, newName: string) => {
  try {
    // Create new workflow with new name
    const workflowData = { name: newName }

    const createResponse = await fetch(`${API_BASE}/workflows`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(workflowData)
    })

    if (!createResponse.ok) {
      throw new Error(`Failed to create workflow: ${createResponse.statusText}`)
    }

    // Delete old workflow
    const deleteResponse = await fetch(`${API_BASE}/workflows/${encodeURIComponent(oldName)}`, {
      method: 'DELETE'
    })

    if (!deleteResponse.ok) {
      throw new Error(`Failed to delete old workflow: ${deleteResponse.statusText}`)
    }

    // Update tab name
    updateActiveTabName(newName)

    console.log('Workflow renamed successfully:', oldName, '->', newName)
  } catch (error) {
    console.error('Error renaming workflow:', error)
  }
}

// Create new workflow via POST API
const createWorkflow = async (name: string) => {
  try {
    const workflowData = {
      name: name
    }

    const response = await fetch(`${API_BASE}/workflows`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(workflowData)
    })

    if (!response.ok) {
      throw new Error(`Failed to create workflow: ${response.statusText}`)
    }

    console.log('Workflow created successfully:', name)
  } catch (error) {
    console.error('Error creating workflow:', error)
  }
}

// Update existing workflow via PUT API
const updateWorkflow = async (name: string) => {
  try {
    const workflowData = {
      name: name
    }

    const response = await fetch(`${API_BASE}/workflows/${encodeURIComponent(name)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(workflowData)
    })

    if (!response.ok) {
      throw new Error(`Failed to update workflow: ${response.statusText}`)
    }

    console.log('Workflow updated successfully:', name)
  } catch (error) {
    console.error('Error updating workflow:', error)
  }
}

const deleteWorkflow = () => {
  if (confirm(`Are you sure you want to delete workflow "${currentWorkflow.value}"?`)) {
    console.log('Delete workflow:', currentWorkflow.value)
    showWorkflowMenu.value = false
  }
}

// Dialog handlers
const handleDialogConfirm = async () => {
  const name = nameDialogInput.value.trim()
  if (!name) {
    return // Empty name not allowed
  }
  
  // Check if name already exists (for rename case)
  try {
    const response = await fetch(`${API_BASE}/workflows`)
    if (response.ok) {
      const existing = await response.json()
      if (existing.indexOf(name) !== -1) {
          // Show error message and keep dialog open
          dialogTitle.value = 'Rename Workflow'
          dialogMessage.value = `A workflow named "${name}" already exists. Please choose a different name:`
          hasDialogError.value = true
          return
        }
    }
  } catch (error) {
    console.error('Failed to check existing workflows:', error)
  }
  
  showNameDialog.value = false
  hasDialogError.value = false
  
  // Update the workflow name
  updateActiveTabName(name)
  currentWorkflow.value = name
  
  // Create the workflow
  await createWorkflow(name)
  attachTab(activeTabId.value)
  
  showWorkflowMenu.value = false
}

const handleDialogCancel = () => {
  showNameDialog.value = false
  hasDialogError.value = false
  nameDialogInput.value = ''
}
</script>

<template>
  <div class="floating-buttons">
    <!-- Left side buttons -->
    <div class="floating-left">
      <!-- Workflow button with dropdown or rename input -->
      <div v-if="isRenaming" class="d-flex ga-2">
        <v-text-field
          ref="renameInput"
          v-model="currentWorkflow"
          variant="outlined"
          density="compact"
          :error-messages="renameError"
          @keydown.enter="validateAndFinishRename"
          @keydown.escape="cancelRename"
          @blur="validateAndFinishRename"
          style="width: 200px"
        ></v-text-field>
      </div>
      <v-menu v-else v-model="showWorkflowMenu" :close-on-content-click="false">
        <template v-slot:activator="{ props }">
          <v-btn
            v-bind="props"
            variant="outlined"
            append-icon="mdi-chevron-down"
            @dblclick="renameWorkflow"
            style="text-transform: none;"
          >
            {{ workflowDisplayName }}
          </v-btn>
        </template>
        <v-list density="compact" nav>
          <v-list-item @click="duplicateWorkflow">
            <template v-slot:prepend>
              <v-icon>mdi-content-copy</v-icon>
            </template>
            <v-list-item-title>Duplicate</v-list-item-title>
          </v-list-item>
          <v-list-item @click="saveWorkflow">
            <template v-slot:prepend>
              <v-icon>mdi-content-save</v-icon>
            </template>
            <v-list-item-title>Save</v-list-item-title>
          </v-list-item>
          <v-list-item @click="saveAsWorkflow">
            <template v-slot:prepend>
              <v-icon>mdi-content-save-edit</v-icon>
            </template>
            <v-list-item-title>Save As</v-list-item-title>
          </v-list-item>
          <v-list-item @click="renameWorkflow">
            <template v-slot:prepend>
              <v-icon>mdi-pencil</v-icon>
            </template>
            <v-list-item-title>Rename</v-list-item-title>
          </v-list-item>
          <v-divider></v-divider>
          <v-list-item @click="deleteWorkflow" class="text-error">
            <template v-slot:prepend>
              <v-icon color="error">mdi-delete</v-icon>
            </template>
            <v-list-item-title class="text-error">Delete</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <!-- Workspace button -->
      <v-btn variant="outlined" disabled>
        {{ workspaceName }}
      </v-btn>
    </div>

    <!-- Right side button -->
    <div class="floating-right">
      <v-btn variant="flat" color="primary" @click="console.log('Run workflow')">
        <v-icon start>mdi-play</v-icon>
        Run
      </v-btn>
    </div>

    <!-- Workflow Name Dialog -->
    <v-dialog v-model="showNameDialog" max-width="400" persistent>
      <v-card>
        <v-card-title>{{ dialogTitle }}</v-card-title>
        <v-card-text>
          <p class="mb-4" :class="hasDialogError ? 'text-error' : ''">{{ dialogMessage }}</p>
          <v-text-field
            v-model="nameDialogInput"
            label="Workflow Name"
            variant="outlined"
            density="compact"
            autofocus
            @keyup.enter="handleDialogConfirm"
            @keyup.escape="handleDialogCancel"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="handleDialogCancel">Cancel</v-btn>
          <v-btn
            color="primary"
            @click="handleDialogConfirm"
            :disabled="!nameDialogInput.trim()"
          >
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
/* Floating buttons - responsive positioning */
.floating-buttons {
  position: absolute;
  top: 5.5rem; /* Space from app bar */
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 0 clamp(2rem, 5vw, 4rem); /* Responsive padding */
  pointer-events: none;
  z-index: 10;
}

.floating-left,
.floating-right {
  display: flex;
  flex-direction: row;
  gap: 0.5rem; /* Gap between buttons */
  pointer-events: auto;
  align-items: center;
}

.floating-left {
  align-items: flex-start;
}

.floating-right {
  align-items: flex-end;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .floating-buttons {
    top: 3.5rem;
    padding: 0 1rem;
  }

  .floating-left,
  .floating-right {
    gap: 0.25rem;
  }
}

@media (max-width: 480px) {
  .floating-buttons {
    top: 3rem;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
  }

  .floating-left {
    flex-direction: row;
    order: 2;
  }

  .floating-right {
    order: 1;
  }
}
</style>
