<script setup lang="ts">
import { ref, inject, onMounted } from 'vue'
import { createTab } from '../models/tabs'
import { createWorkflow, workflowNameExists, listWorkflows } from '../api/workflow'
import { Workflow } from '../models/workflow'

// Inject error handler from parent
const showError = inject<(message: string) => void>('showError', (msg: string) => {
  console.error('Error (no handler):', msg)
})

// Dialog state
const nameDialogInput = ref('')
const showNameDialog = ref(false)

// Existing workflows
const existingWorkflows = ref<string[]>([])
const isLoading = ref(false)

// Load workflows on mount
onMounted(async () => {
  await loadWorkflows()
})

const loadWorkflows = async () => {
  isLoading.value = true
  try {
    existingWorkflows.value = await listWorkflows()
  } catch (error) {
    console.error('Failed to load workflows:', error)
  } finally {
    isLoading.value = false
  }
}

const handleNewTab = () => {
  showNameDialog.value = true
}

const openWorkflow = async (workflowName: string) => {
  try {
    await createTab(workflowName)
  } catch (error) {
    showError(`Failed to open workflow "${workflowName}": ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

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
  nameDialogInput.value = ''
}
</script>

<template>
  <div class="welcome-container">
    <div class="welcome-content">
      <h1 class="welcome-title">Welcome to ATTPC Flow</h1>
      <p class="welcome-subtitle">
        A visual workflow editor for AT-TPC data analysis
      </p>
      <v-btn
        color="primary"
        size="large"
        prepend-icon="mdi-plus"
        @click="handleNewTab"
        class="new-tab-btn"
      >
        Open New Workflow
      </v-btn>

      <!-- Existing Workflows Section -->
      <div v-if="existingWorkflows.length > 0" class="workflows-section">
        <h2 class="workflows-title">Recent Workflows</h2>
        <v-list class="workflows-list" bg-color="transparent">
          <v-list-item
            v-for="workflow in existingWorkflows"
            :key="workflow"
            class="workflow-item"
            @click="openWorkflow(workflow)"
            prepend-icon="mdi-file-tree"
          >
            <v-list-item-title>{{ workflow }}</v-list-item-title>
            <template v-slot:append>
              <v-icon icon="mdi-chevron-right" size="small" color="grey-lighten-1" />
            </template>
          </v-list-item>
        </v-list>
      </div>

      <div v-else-if="!isLoading" class="no-workflows">
        <p class="text-grey-lighten-1">No workflows found. Create your first workflow to get started.</p>
      </div>
    </div>

    <!-- Name Dialog for New Workflow -->
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
            Open
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.welcome-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1e1e1e;
  overflow-y: auto;
}

.welcome-content {
  text-align: center;
  color: #ffffff;
  padding: 2rem;
  max-width: 600px;
  width: 100%;
}

.welcome-title {
  font-size: 2.5rem;
  font-weight: 300;
  margin-bottom: 1rem;
  color: #ffffff;
}

.welcome-subtitle {
  font-size: 1.1rem;
  color: #a0a0a0;
  margin-bottom: 2rem;
}

.new-tab-btn {
  text-transform: none;
  font-weight: 500;
  margin-bottom: 3rem;
}

.workflows-section {
  text-align: left;
  margin-top: 1rem;
}

.workflows-title {
  font-size: 1rem;
  font-weight: 500;
  color: #a0a0a0;
  margin-bottom: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.workflows-list {
  border-radius: 8px;
  overflow: hidden;
}

.workflow-item {
  cursor: pointer;
  transition: background-color 0.2s ease;
  border-radius: 8px;
  margin-bottom: 4px;
}

.workflow-item:hover {
  background-color: rgba(255, 255, 255, 0.05);
}

.no-workflows {
  margin-top: 2rem;
  color: #808080;
}
</style>
