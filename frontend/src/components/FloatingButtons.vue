<script setup lang="ts">
import { ref, computed, nextTick, watch, inject, defineAsyncComponent } from 'vue'
import { type WorkflowRun } from '../models/workflow'
import {
  activeTabName,
  activeWorkspace,
  activeWorkers,
  activeWorkflow,
  saveActiveTab,
  renameActiveTab,
  deleteActiveTab,
  activeWorkflowChangeRun,
  activeWorkflowChangeWorkspace,
  activeWorkflowChangeWorkers
} from '../models/tabs'
import {
  listWorkflows,
  executeWorkflow,
} from '../api/workflow'
import { useProgressWebSocket } from '../composables/useWebSocket'

// Lazy load RunSelector only when needed
const RunSelector = defineAsyncComponent(() => import('./RunSelector.vue'))

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
const isExecuting = ref(false)

// WebSocket management
const { connect } = useProgressWebSocket()
const workersInput = ref<HTMLInputElement>()
const renameError = ref('')
const existingWorkflows = ref<string[]>([])


const showDeleteDialog = ref(false)

// Update workflow name when store changes
watch(activeTabName, (newName) => {
  currentWorkflow.value = newName || ''
})

// Computed
const workflowDisplayName = computed(() => activeTabName.value || 'untitled')

// Workflow functions
const duplicateWorkflow = () => {
  // const currentWorkflow = JSON.parse(JSON.stringify(activeWorkflow.value))
  // addNewTab()
  // currentWorkflow.name = null
  // updateActiveWorkflow(currentWorkflow)
  // showWorkflowMenu.value = false

  // TODO
  console.log("TODO: duplicate workflow")
  showWorkflowMenu.value = false
}

const saveAsWorkflow = () => {
  console.log('SaveAs: TODO - not implemented yet')
  showWorkflowMenu.value = false
}

const saveWorkflow = () => {
  saveActiveTab()
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

  try {
    // Check against existing workflow files
    if (existingWorkflows.value.indexOf(newName) !== -1) {
      renameError.value = 'A workflow with this name already exists'
      return
    }
    // For attached tabs, create new and delete old via API
    await renameActiveTab(newName)
    isRenaming.value = false
    renameError.value = ''
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

const handleDeleteWorkflow = () => {
  // Show the delete confirmation dialog
  showDeleteDialog.value = true
  showWorkflowMenu.value = false
}

// Delete dialog handlers
const handleDeleteConfirm = async () => {
  // Hide the dialog
  showDeleteDialog.value = false
  try {
    deleteActiveTab()
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to delete workflow'
    showError(errorMessage)
  }
}

const handleDeleteCancel = () => {
  showDeleteDialog.value = false
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
    activeWorkflowChangeWorkspace(workspaceName.value)
    console.log('Workspace path updated to:', activeWorkspace.value)
  }
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
    activeWorkflowChangeWorkers(workersCount.value ?? 2)
    console.log('Workers count updated to:', workersCount.value ?? 2)
  }
}

const cancelEditWorkers = () => {
  isEditingWorkers.value = false
}

const runWorkflow = async () => {
  try {
    // Step 1: Save the workflow (saveWorkflow handles all validation)
    await saveActiveTab()

    // Step2: Check if workspace and max_workers are set
    if (!workspaceName.value || !workersCount.value) {
      showError('Please set workspace and max_workers before running the workflow')
      return
    }

    // Step 3: Execute the workflow
    const workflowName = activeTabName.value
    if (!workflowName) {
      showError('Failed to save workflow before execution')
      return
    }

    // Set executing state
    isExecuting.value = true

    console.log(`Executing workflow: ${workflowName}`)
    const executionStatus = await executeWorkflow(workflowName)
    console.log('Workflow execution started:', executionStatus)

    // Connect to WebSocket for completion notification
    connect("startBtn", {
      onExecutionComplete: (execution_id: string) => {
        if (execution_id != executionStatus.execution_id) {
          return
        }
        // Handle completion
        console.log('Execution completed')
        isExecuting.value = false
      },
      onError: (error: Event) => {
        console.error('WebSocket error:', error)
        // Reset executing state on WebSocket error
        isExecuting.value = false
      }
    })

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to save or execute workflow'
    showError(errorMessage)
    // Reset executing state on error
    isExecuting.value = false
  }
}

// Run number selector state
const showRunNumberSheet = ref(false)
const runInfo = ref<WorkflowRun>({runs: [], tags: []})

const handleRunNumberSelection = (value: WorkflowRun) => {
  if (activeWorkflow.value) {
    runInfo.value = value
    activeWorkflowChangeRun(value)
    console.log('Updated workflow runNumbers and tags:', runInfo.value.runs, runInfo.value.tags)
  }
  showRunNumberSheet.value = false
}

// Watch for workspace changes from store
watch(activeWorkspace, (newWorkspace) => {
  workspaceName.value = newWorkspace
})

// Watch for workers changes from store
watch(activeWorkers, (newWorkers) => {
  workersCount.value = newWorkers
})

// Watch for workflow changes to sync runNumbers
watch(activeWorkflow, (newWorkflow) => {
  if (newWorkflow && newWorkflow.run) {
    runInfo.value = newWorkflow.run
  }
}, { immediate: true })

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

    <!-- Right side buttons -->
    <div class="floating-right">
      <!-- Run Number Selector Menu -->
      <v-menu
        v-model="showRunNumberSheet"
        :close-on-content-click="false"
        location="bottom end"
        :offset="[10, 8]"
      >
        <template v-slot:activator="{ props }">
          <v-btn variant="outlined" v-bind="props" :disabled="!activeWorkspace">
            <v-icon start>mdi-format-list-numbered</v-icon>
            {{ runInfo.runs.length }} run{{ runInfo.runs.length === 1 ? '' : 's' }}
          </v-btn>
        </template>

        <RunSelector
          :runInfo="runInfo"
          @close="showRunNumberSheet = false"
          @apply="handleRunNumberSelection"
        />
      </v-menu>

      <!-- Run Button -->
      <v-btn
        variant="flat"
        color="primary"
        @click="runWorkflow"
        :disabled="isExecuting"
      >
        <v-icon start v-show="!isExecuting">{{ 'mdi-play' }}</v-icon>
        {{ isExecuting ? 'Processing...' : 'Start' }}
      </v-btn>
      <v-progress-circular color="primary" indeterminate class="mt-2" v-show="isExecuting"></v-progress-circular>
    </div>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="showDeleteDialog" max-width="400" persistent>
      <v-card>
        <v-card-title>Confirm delete</v-card-title>
        <v-card-text>
          <p>{{ `Are you sure you want to delete workflow "${currentWorkflow}"? This will permanently delete the workflow file.` }}</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="handleDeleteCancel">Cancel</v-btn>
          <v-btn
            color="error"
            @click="handleDeleteConfirm"
          >
            Delete
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