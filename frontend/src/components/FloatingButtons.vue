<script setup lang="ts">
import { ref, computed, nextTick, watch, inject } from 'vue'
import {
  activeTabName,
  activeTabId,
  activeWorkspace,
  activeWorkers,
  isTabAttached,
  getOtherTabNames,
  addNewTab,
  updateActiveTabName,
  updateActiveWorkflow,
  setActiveWorkflow,
  saveTab,
  deleteTab,
  activeWorkflow
} from '../stores/tabs'
import {
  type Workflow,
  copyWorkflow,
} from '../stores/workflow'
import {
  createWorkflow,
  updateWorkflow as updateWorkflowService,
  deleteWorkflow,
  listWorkflows,
  workflowNameExists,
  executeWorkflow,
} from '../api/workflow'

// Inject error handler from parent
const showError = inject<(message: string) => void>('showError', (msg: string) => {
  console.error('Error (no handler):', msg)
})

// Local state
const showWorkflowMenu = ref(false)
const isRenaming = ref(false)
const renameInput = ref<HTMLInputElement>()
const currentWorkflow = ref(activeTabName.value || '')
const workspaceName = ref(activeWorkspace.value)
const isEditingWorkspace = ref(false)
const workspaceInput = ref<HTMLInputElement>()
const workersCount = ref(activeWorkers.value)
const isEditingWorkers = ref(false)
const workersInput = ref<HTMLInputElement>()
const renameError = ref('')
const existingWorkflows = ref<string[]>([])
const otherTabNames = ref<string[]>([])

// Dialog states organized in a structured object
const dialogs = ref({
  // Name dialog for save/rename workflow
  name: {
    show: false,
    title: '',
    message: '',
    input: '',
    hasError: false
  },
  // Delete confirmation dialog
  delete: {
    show: false,
    title: '',
    message: '',
    workflowName: '',
    isAttached: false
  }
})

// Update workflow name when store changes
watch(activeTabName, (newName) => {
  currentWorkflow.value = newName || ''
})

// Computed
const workflowDisplayName = computed(() => activeTabName.value || 'untitled')

// Workflow functions
const duplicateWorkflow = () => {
  const currentWorkflow = JSON.parse(JSON.stringify(activeWorkflow.value))
  addNewTab()
  currentWorkflow.name = null
  updateActiveWorkflow(currentWorkflow)
  showWorkflowMenu.value = false
}

const saveWorkflow = async () => {
  const workflowName = currentWorkflow.value?.trim()
  const currentTabId = activeTabId.value
  const isAttachedTab = isTabAttached(currentTabId)

  try {
    if (isAttachedTab) {
      // Attached tab: just update
      if (workflowName) {
        await updateWorkflowService()
      }
    } else {
      // Unattached tab
      if (!workflowName) {
        // Show dialog to enter workflow name
        dialogs.value.name.title = 'Save Workflow'
        dialogs.value.name.message = 'Please enter a name for this workflow:'
        dialogs.value.name.input = ''
        dialogs.value.name.hasError = false
        dialogs.value.name.show = true
        return
      }

      // Check if name already exists
      const nameExists = await workflowNameExists(workflowName)
      if (nameExists) {
        // Name already exists, show dialog with current name
        dialogs.value.name.title = 'Rename Workflow'
        dialogs.value.name.message = `A workflow named "${workflowName}" already exists. Please choose a different name:`
        dialogs.value.name.input = workflowName
        dialogs.value.name.hasError = true
        dialogs.value.name.show = true
        return
      }

      // Name doesn't exist, proceed with save
      // Set activeWorkflow first so createWorkflow uses the correct data
      setActiveWorkflow(copyWorkflow(activeWorkflow.value as Workflow, workflowName))
      await createWorkflow()
      saveTab(currentTabId)
    }

    showWorkflowMenu.value = false
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to save workflow'
    showError(errorMessage)
    showWorkflowMenu.value = false
  }
}

const saveAsWorkflow = () => {
  console.log('SaveAs: TODO - not implemented yet')
  showWorkflowMenu.value = false
}

const renameWorkflow = async () => {
  isRenaming.value = true
  showWorkflowMenu.value = false
  renameError.value = ''

  try {
    // Fetch existing workflows for validation
    existingWorkflows.value = await listWorkflows()
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to fetch workflows'
    showError(errorMessage)
    isRenaming.value = false
    return
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

  try {
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
      // Check against existing workflow files
      if (existingWorkflows.value.indexOf(newName) !== -1) {
        renameError.value = 'A workflow with this name already exists'
        return
      } else if (otherTabNames.value.indexOf(newName) !== -1) {
        renameError.value = 'Another tab already has this name'
        return
      }
      // Valid - update name directly
      updateActiveTabName(newName)
      isRenaming.value = false
      renameError.value = ''
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to rename workflow'
    showError(errorMessage)
    renameError.value = errorMessage
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
    // Update workflow
    setActiveWorkflow(copyWorkflow(activeWorkflow.value as Workflow, newName))

    // Create new workflow with new name
    await createWorkflow()

    // Temporarily set activeTabName back to old name to delete it
    updateActiveTabName(oldName)

    // Delete old workflow
    try {
      await deleteWorkflow()
    } catch (deleteError) {
      console.warn('Failed to delete old workflow, but new workflow was created')
      showError('Failed to delete old workflow, but new workflow was created')
    } finally {
      // Always restore the new name
      updateActiveTabName(newName)
    }

    // Mark tab as saved
    saveTab(activeTabId.value)

    console.log('Workflow renamed successfully:', oldName, '->', newName)
  } catch (error) {
    // Revert name change on error
    updateActiveTabName(oldName)
    setActiveWorkflow(copyWorkflow(activeWorkflow.value as Workflow, oldName))
    throw error
  }
}

const handleDeleteWorkflow = () => {
  const currentTabId = activeTabId.value
  const workflowName = currentWorkflow.value
  const isAttached = isTabAttached(currentTabId)

  if (isAttached && workflowName) {
    // Attached tab - set up delete confirmation for workflow
    dialogs.value.delete.title = 'Delete Workflow'
    dialogs.value.delete.message = `Are you sure you want to delete workflow "${workflowName}"? This will permanently delete the workflow file.`
    dialogs.value.delete.workflowName = workflowName
    dialogs.value.delete.isAttached = true
  } else {
    // Unattached tab - set up delete confirmation for unsaved tab
    dialogs.value.delete.title = 'Close Unsaved Tab'
    dialogs.value.delete.message = 'Are you sure you want to close this unsaved tab?'
    dialogs.value.delete.workflowName = ''
    dialogs.value.delete.isAttached = false
  }

  // Show the delete confirmation dialog
  dialogs.value.delete.show = true
  showWorkflowMenu.value = false
}

// Dialog handlers
const handleDialogConfirm = async () => {
  const name = dialogs.value.name.input.trim()
  if (!name) {
    return // Empty name not allowed
  }

  try {
    // Check if name already exists (for rename case)
    const nameExists = await workflowNameExists(name)
    if (nameExists) {
      // Show error message and keep dialog open
      dialogs.value.name.title = 'Rename Workflow'
      dialogs.value.name.message = `A workflow named "${name}" already exists. Please choose a different name:`
      dialogs.value.name.hasError = true
      return
    }

    dialogs.value.name.show = false
    dialogs.value.name.hasError = false

    // Update the workflow name
    updateActiveTabName(name)
    currentWorkflow.value = name

    // Set activeWorkflow first so createWorkflow uses the correct data
    setActiveWorkflow(copyWorkflow(activeWorkflow.value as Workflow, name))
    // Create the workflow
    await createWorkflow()
    saveTab(activeTabId.value)

    showWorkflowMenu.value = false
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to save workflow'
    showError(errorMessage)
    dialogs.value.name.hasError = true
  }
}

const handleDialogCancel = () => {
  dialogs.value.name.show = false
  dialogs.value.name.hasError = false
  dialogs.value.name.input = ''
}

// Delete dialog handlers
const handleDeleteConfirm = async () => {
  const currentTabId = activeTabId.value
  const { workflowName, isAttached } = dialogs.value.delete

  // Hide the dialog
  dialogs.value.delete.show = false

  if (isAttached && workflowName) {
    // Attached tab - delete workflow from server
    try {
      await deleteWorkflow()
      // Close the tab after successful deletion
      deleteTab(currentTabId)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete workflow'
      showError(errorMessage)
    }
  } else {
    // Unattached tab - just close
    deleteTab(currentTabId)
  }
}

const handleDeleteCancel = () => {
  dialogs.value.delete.show = false
}

const startEditWorkspace = () => {
  isEditingWorkspace.value = true
  nextTick(() => {
    workspaceInput.value?.focus()
    workspaceInput.value?.select()
  })
}

const finishEditWorkspace = () => {
  isEditingWorkspace.value = false
  if (activeWorkflow.value) {
    activeWorkflow.value.workspace = workspaceName.value
  }
  console.log('Workspace path updated to:', activeWorkspace.value)
}

const cancelEditWorkspace = () => {
  isEditingWorkspace.value = false
}

const startEditWorkers = () => {
  isEditingWorkers.value = true
  nextTick(() => {
    workersInput.value?.focus()
    workersInput.value?.select()
  })
}

const finishEditWorkers = () => {
  isEditingWorkers.value = false
  // Update workers count in the active workflow
  if (activeWorkflow.value) {
    activeWorkflow.value.workers = workersCount.value ?? 2
  }
  console.log('Workers count updated to:', workersCount.value ?? 2)
}

const cancelEditWorkers = () => {
  isEditingWorkers.value = false
}

const runWorkflow = async () => {
  try {
    // Step 1: Save the workflow (saveWorkflow handles all validation)
    await saveWorkflow()

    // Step2: Check if workspace and max_workers are set
    if (!workspaceName.value || !workersCount.value) {
      showError('Please set workspace and max_workers before running the workflow')
      return
    }

    // Step 2: Execute the workflow
    const finalWorkflowName = activeTabName.value
    if (!finalWorkflowName) {
      showError('Failed to save workflow before execution')
      return
    }

    console.log(`Executing workflow: ${finalWorkflowName}`)
    const executionStatus = await executeWorkflow(finalWorkflowName)
    console.log('Workflow execution started:', executionStatus)
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to save or execute workflow'
    showError(errorMessage)
  }
}

// Watch for workspace changes from store
watch(activeWorkspace, (newWorkspace) => {
  workspaceName.value = newWorkspace
})

// Watch for workers changes from store
watch(activeWorkers, (newWorkers) => {
  workersCount.value = newWorkers
})

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
          <v-list-item @click="handleDeleteWorkflow" class="text-error">
            <template v-slot:prepend>
              <v-icon color="error">mdi-delete</v-icon>
            </template>
            <v-list-item-title class="text-error">Delete</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <!-- Workspace button or input -->
      <div v-if="!isEditingWorkspace" class="d-flex align-center">
        <v-btn
          variant="outlined"
          @click="startEditWorkspace"
          class="workspace-btn"
          :class="{ 'workspace-null': !workspaceName }"
        >
          <v-icon start size="small" style="opacity: 0.7">mdi-folder-outline</v-icon>
          <span class="workspace-label">{{ workspaceName || 'No workspace' }}</span>
        </v-btn>
      </div>
      <v-text-field
        v-else
        ref="workspaceInput"
        v-model="workspaceName"
        variant="outlined"
        density="compact"
        placeholder="Enter workspace path..."
        style="width: 300px;"
        @keyup.enter="finishEditWorkspace"
        @keyup.escape="cancelEditWorkspace"
        @blur="finishEditWorkspace"
      ></v-text-field>

      <!-- Workers button or input -->
      <div v-if="!isEditingWorkers" class="d-flex align-center">
        <v-btn
          variant="outlined"
          @click="startEditWorkers"
          class="workers-btn"
        >
          <v-icon start size="small" style="opacity: 0.7">mdi-account-group-outline</v-icon>
          <span class="workers-number">{{ activeWorkers }}</span>
          <span class="workers-label">cores</span>
        </v-btn>
      </div>
      <v-text-field
        v-else
        ref="workersInput"
        v-model.number="workersCount"
        variant="outlined"
        density="compact"
        type="number"
        min="1"
        max="16"
        placeholder="Number of workers..."
        style="width: 150px;"
        @keyup.enter="finishEditWorkers"
        @keyup.escape="cancelEditWorkers"
        @blur="finishEditWorkers"
      ></v-text-field>
    </div>

    <!-- Right side button -->
    <div class="floating-right">
      <v-btn variant="flat" color="primary" @click="runWorkflow">
        <v-icon start>mdi-play</v-icon>
        Run
      </v-btn>
    </div>

    <!-- Workflow Name Dialog -->
    <v-dialog v-model="dialogs.name.show" max-width="400" persistent>
      <v-card>
        <v-card-title>{{ dialogs.name.title }}</v-card-title>
        <v-card-text>
          <p class="mb-4" :class="dialogs.name.hasError ? 'text-error' : ''">{{ dialogs.name.message }}</p>
          <v-text-field
            v-model="dialogs.name.input"
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
            :disabled="!dialogs.name.input.trim()"
          >
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="dialogs.delete.show" max-width="400" persistent>
      <v-card>
        <v-card-title>{{ dialogs.delete.title }}</v-card-title>
        <v-card-text>
          <p>{{ dialogs.delete.message }}</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="handleDeleteCancel">Cancel</v-btn>
          <v-btn
            color="error"
            @click="handleDeleteConfirm"
          >
            {{ dialogs.delete.isAttached ? 'Delete' : 'Close' }}
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

/* Workspace button styles */
.workspace-btn {
  text-transform: none !important;
}

.workspace-btn .workspace-label {
  text-transform: none;
}

.workspace-btn.workspace-null .workspace-label {
  color: rgba(var(--v-theme-on-surface), 0.5);
}

/* Workers button styles */
.workers-btn {
  text-transform: none !important;
}

.workers-btn .workers-number {
  text-transform: none;
  font-weight: 600;
}

.workers-btn .workers-label {
  text-transform: none;
  opacity: 0.7;
  margin-left: 6px;
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