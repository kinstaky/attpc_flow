<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { listExecutions } from '../api/workflow'
import {
  useProgressWebSocket,
  ExecutionStatus,
  TaskProgress,
} from '../composables/useWebSocket'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const executions = ref<Array<ExecutionStatus>>([])
const tasks = ref<Record<string, Record<string, TaskProgress>>>({})
const loading = ref(false)
const opened = ref<Array<string>>([])
const error = ref<string | null>(null)

// WebSocket management
const { connect, disconnect, isConnectionActive } = useProgressWebSocket()

watch(
  () => props.visible,
  (newVisible, oldVisible) => {
    if (newVisible && !oldVisible) {
      console.log("Open progress panel")
      connect("progressPanel", {
        onTaskProgress: (execution_id: string, progress: Record<string, TaskProgress>) => {
          tasks.value[execution_id] = progress
        },
        onExecutionProgress: (progress: Array<ExecutionStatus>) => {
          executions.value = progress
        },
        onExecutionComplete: (_execution_id: string, progress: Array<ExecutionStatus>) => {
          executions.value = progress
          disconnect("progressPanel")
        },
        onError: (event: Event) => {
          console.error('WebSocket error:', event)
        }
      })
    } else if (!newVisible && oldVisible) {
      console.log("Close progress panel")
      disconnect("progressPanel")
    }
  }
)

// Fetch executions from API
const fetchExecutions = async () => {
  try {
    loading.value = true
    error.value = null
    executions.value = await listExecutions()
    console.log(executions.value)
    console.log(opened.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to fetch executions'
    console.error('Failed to fetch executions:', err)
  } finally {
    loading.value = false
  }
}

// Status mappings - DRY approach
const STATUS_CONFIG = {
  completed: { color: 'success', icon: 'mdi-check-circle' },
  running: { color: 'info', icon: 'mdi-play-circle' },
  failed: { color: 'error', icon: 'mdi-close-circle' },
  waiting: { color: 'warning', icon: 'mdi-clock' },
  default: { color: 'grey', icon: 'mdi-help-circle' }
} as const

// Helper functions
const getStatusConfig = (status: string) =>
  STATUS_CONFIG[status as keyof typeof STATUS_CONFIG] ||
  STATUS_CONFIG.default

const formatTime = (timestamp: number | null) => {
  if (!timestamp) return 'Not started'
  return new Date(timestamp*1000).toLocaleString()
}

const formatPercentage = (percentage: number) => `${Math.round(percentage)}%`

const getTaskProgressColor = (percentage: number) => {
  // Use array-based approach for progress thresholds
  const thresholds = [
    { min: 100, color: 'success' },
    { min: 0, color: 'info' },
  ]

  return thresholds.find(threshold => percentage >= threshold.min)?.color || 'grey'
}

const getExecutionProgress = (execution: ExecutionStatus) => {
  if (execution.total_tasks > 0) {
    return Math.round(execution.completed_tasks / execution.total_tasks * 100)
  }
  return 0
}

// Initialize and cleanup
onMounted(() => {
  fetchExecutions()
})

onUnmounted(() => {
  if (isConnectionActive("progressPanel")) {
    disconnect("progressPanel")
  }
})
</script>

<template>
  <v-navigation-drawer
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    temporary
    width="800"
    location="left"
    class="status-panel"
  >
    <v-toolbar flat>
      <span class="text-h6 pl-4">Progress</span>
      <v-spacer></v-spacer>
      <v-btn
        icon
        variant="text"
        @click="fetchExecutions"
        :loading="loading"
        title="Refresh executions"
      >
        <v-icon>mdi-refresh</v-icon>
      </v-btn>
      <v-btn icon variant="text" @click="$emit('update:visible', false)">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-toolbar>

    <div class="pa-3">
      <!-- Loading state -->
      <div v-if="loading" class="text-center py-4">
        <v-progress-circular indeterminate size="24" class="mr-2" />
        Loading executions...
      </div>

      <!-- Error state -->
      <div v-if="error" class="text-center py-4">
        <v-alert type="error" variant="tonal" class="mb-2">
          {{ error }}
        </v-alert>
        <div class="text-caption">Use the refresh button in the toolbar to retry</div>
      </div>

      <!-- Empty state -->
      <div
        v-if="!loading && !error && executions.length === 0"
        class="text-center py-4 text-grey"
      >
        <v-icon size="48" class="mb-2">mdi-clipboard-text-outline</v-icon>
        <div>No executions found</div>
        <div class="text-caption">Start a workflow to see execution progress</div>
      </div>

      <!-- Executions list -->
      <v-list
        :opened="opened"
        density="compact"
        v-if="executions.length > 0"
      >
        <v-list-group
          v-for="status in executions"
          :value="status.execution_id"
          :key="status.execution_id"
        >
          <template #activator="{ props }">
            <v-list-item
              v-bind="props"
              class="execution-item"
            >
              <template v-slot:prepend>
                <v-icon :color="getStatusConfig(status.status).color">
                  {{ getStatusConfig(status.status).icon }}
                </v-icon>
              </template>

              <v-list-item-title>
                {{ status.execution_id }}
                <v-chip
                  :color="getStatusConfig(status.status).color"
                  size="x-small"
                  class="ml-2"
                >
                  {{ status.status }}
                </v-chip>
              </v-list-item-title>

              <v-list-item-subtitle>
                {{ status.workflow_id }} • {{ formatTime(status.started_at) }}
                <span v-if="status.status == 'completed' || status.status == 'failed'">
                  • {{ formatTime(status.completed_at) }}
                </span>
                • {{ status.completed_tasks }}/{{ status.total_tasks }} tasks
              </v-list-item-subtitle>

              <!-- Progress bar for execution -->
              <div class="mt-2">
                <v-progress-linear
                  :model-value="getExecutionProgress(status)"
                  :color="getStatusConfig(status.status).color"
                  height="4"
                />
              </div>
            </v-list-item>
          </template>
          <v-list-item
            v-for="(progress, taskId) in tasks[status.execution_id]"
            :key="taskId"
            class="task-item mb-2"
          >
            <v-list-item-title>
              {{ progress.task_name || "Task " + taskId }}
              <span v-if="progress.run"> • run {{ progress.run }}</span>
              <v-chip
                :color="getStatusConfig(progress.status).color"
                size="x-small"
                class="ml-2"
              >
                {{ progress.status }}
              </v-chip>
            </v-list-item-title>
            <v-progress-linear
              :model-value="progress.percentage"
              :color="getTaskProgressColor(progress.percentage)"
              height="3"
              class="mt-1"
            />
            <template v-slot:append>
              {{ formatPercentage(progress.percentage) }}
            </template>
          </v-list-item>
        </v-list-group>
      </v-list>
    </div>
  </v-navigation-drawer>
</template>

<style scoped>
.execution-item {
  cursor: pointer;
}

.execution-item:hover {
  background-color: rgba(var(--v-theme-surface-variant), 0.12);
}

.task-details {
  padding-left: 16px;
}

.task-item {
  background-color: rgba(var(--v-theme-surface), 0.5);
  border-radius: 4px;
  padding: 8px;
}

/* Position the panel to the right of the side nav */
:deep(.status-panel) {
  left: 56px !important;
}
</style>
