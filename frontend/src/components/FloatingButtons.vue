<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { workflowState, activeTabName } from '../stores/workflow'

// Emits
const emit = defineEmits<{
  workflowAction: [action: string, data?: any]
}>()

// Local state
const showWorkflowMenu = ref(false)
const isRenaming = ref(false)
const renameInput = ref<HTMLInputElement>()
const currentWorkflow = ref(activeTabName.value)
const workspaceName = ref('Workspace 1')

// Update workflow name when store changes
watch(activeTabName, (newName) => {
  currentWorkflow.value = newName
})

// Computed
const workflowDisplayName = computed(() => currentWorkflow.value)

// Workflow functions
const duplicateWorkflow = () => {
  emit('workflowAction', 'duplicate')
  showWorkflowMenu.value = false
}

const saveWorkflow = () => {
  emit('workflowAction', 'save', currentWorkflow.value)
  showWorkflowMenu.value = false
}

const saveAsWorkflow = () => {
  emit('workflowAction', 'saveAs')
  showWorkflowMenu.value = false
}

const renameWorkflow = () => {
  isRenaming.value = true
  showWorkflowMenu.value = false
  nextTick(() => {
    renameInput.value?.focus()
    renameInput.value?.select()
  })
}

const finishRename = () => {
  if (renameInput.value?.value.trim()) {
    const newName = renameInput.value.value.trim()
    currentWorkflow.value = newName
    workflowState.updateActiveTabName(newName)
    emit('workflowAction', 'rename', newName)
  }
  isRenaming.value = false
}

const cancelRename = () => {
  isRenaming.value = false
}

const deleteWorkflow = () => {
  if (confirm(`Are you sure you want to delete workflow "${currentWorkflow.value}"?`)) {
    emit('workflowAction', 'delete', currentWorkflow.value)
    showWorkflowMenu.value = false
  }
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
          hide-details
          @keydown.enter="finishRename"
          @keydown.escape="cancelRename"
          @blur="finishRename"
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
      <v-btn variant="flat" color="primary" @click="emit('workflowAction', 'run')">
        <v-icon start>mdi-play</v-icon>
        Run
      </v-btn>
    </div>
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
