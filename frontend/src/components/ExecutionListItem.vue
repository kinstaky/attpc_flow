<script setup lang="ts">
import { ref } from 'vue'
import type { ExecutionStatus, TaskProgress } from '../composables/useWebSocket'
import type { HistoryExecution } from '../api/workflow'

interface Props {
  execution: ExecutionStatus | HistoryExecution
  tasks?: Record<string, TaskProgress>
  isHistory?: boolean
}

const props = defineProps<Props>()
const isExpanded = ref(false)

// Status mappings
const STATUS_CONFIG = {
  completed: { color: 'success', icon: 'mdi-check-circle' },
  running: { color: 'info', icon: 'mdi-play-circle' },
  failed: { color: 'error', icon: 'mdi-close-circle' },
  waiting: { color: 'warning', icon: 'mdi-clock' },
  default: { color: 'grey', icon: 'mdi-help-circle' }
} as const

const getStatusConfig = (status: string) =>
  STATUS_CONFIG[status as keyof typeof STATUS_CONFIG] ||
  STATUS_CONFIG.default

const formatTime = (timestamp: number | null) => {
  if (!timestamp) return 'Not started'
  return new Date(timestamp * 1000).toLocaleString()
}

const formatPercentage = (percentage: number) => `${Math.round(percentage)}%`

const getTaskProgressColor = (percentage: number) => {
  const thresholds = [
    { min: 100, color: 'success' },
    { min: 0, color: 'info' },
  ]
  return thresholds.find(threshold => percentage >= threshold.min)?.color || 'grey'
}

const getExecutionProgress = () => {
  const total = props.execution.total_tasks || 0
  const completed = props.execution.completed_tasks || 0
  if (total > 0) {
    return Math.round(completed / total * 100)
  }
  return 0
}

// Get the tasks to display
const getTasks = (): Record<string, TaskProgress> => {
  if (props.isHistory) {
    return (props.execution as HistoryExecution).tasks || {}
  }
  return props.tasks || {}
}

// Check if execution has started (for active executions)
const getStartedAt = (): number | null => {
  const exec = props.execution as ExecutionStatus
  return exec.started_at || null
}

// Check if execution has completed_at (for active executions)
const getCompletedAt = (): number | null => {
  const exec = props.execution as ExecutionStatus
  return exec.completed_at || null
}

// Get finished_time (for history executions)
const getFinishedTime = (): number | null => {
  return props.execution.completed_at || null
}
</script>

<template>
  <div class="execution-wrapper">
    <v-list-item
      class="execution-item"
      @click="isExpanded = !isExpanded"
    >
      <template v-slot:prepend>
        <v-icon :color="getStatusConfig(execution.status).color">
          {{ getStatusConfig(execution.status).icon }}
        </v-icon>
      </template>

      <v-list-item-title>
        {{ execution.execution_id }}
        <v-chip
          :color="getStatusConfig(execution.status).color"
          size="x-small"
          class="ml-2"
        >
          {{ execution.status }}
        </v-chip>
      </v-list-item-title>

      <v-list-item-subtitle>
        <template v-if="isHistory">
          {{ execution.workflow_id }} • {{ formatTime(getFinishedTime()) }}
        </template>
        <template v-else>
          {{ execution.workflow_id }} • {{ formatTime(getStartedAt()) }}
          <span v-if="execution.status === 'completed' || execution.status === 'failed'">
            • {{ formatTime(getCompletedAt()) }}
          </span>
        </template>
        • {{ execution.completed_tasks || 0 }}/{{ execution.total_tasks || 0 }} tasks
      </v-list-item-subtitle>

      <!-- Progress bar for execution -->
      <div class="mt-2">
        <v-progress-linear
          :model-value="getExecutionProgress()"
          :color="getStatusConfig(execution.status).color"
          height="4"
        />
      </div>

      <template v-slot:append>
        <v-icon>{{ isExpanded ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
      </template>
    </v-list-item>

    <!-- Expanded task list -->
    <v-expand-transition>
      <div v-show="isExpanded" class="task-list">
        <v-list-item
          v-for="(progress, taskId) in getTasks()"
          :key="taskId"
          class="task-item mb-2"
          density="compact"
        >
          <v-list-item-title class="text-body-2">
            {{ progress.task_name || "Task " + taskId }}
            <span v-if="progress.run" class="text-caption text-grey"> • run {{ progress.run }}</span>
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
            <span class="text-caption">{{ formatPercentage(progress.percentage) }}</span>
          </template>
        </v-list-item>
        <v-list-item v-if="Object.keys(getTasks()).length === 0" class="text-grey text-caption">
          No task details available
        </v-list-item>
      </div>
    </v-expand-transition>
  </div>
</template>

<style scoped>
.execution-wrapper {
  border-bottom: 1px solid rgba(var(--v-border-color), 0.12);
}

.execution-item {
  cursor: pointer;
}

.execution-item:hover {
  background-color: rgba(var(--v-theme-surface-variant), 0.12);
}

.task-list {
  padding-left: 16px;
  padding-right: 16px;
  padding-bottom: 8px;
}

.task-item {
  background-color: rgba(var(--v-theme-surface), 0.5);
  border-radius: 4px;
  padding: 8px;
  min-height: 48px;
}
</style>
