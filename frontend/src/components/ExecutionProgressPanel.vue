<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { listExecutions, getExecutionHistory, type HistoryExecution } from '../api/workflow'
import {
  useProgressWebSocket,
  ExecutionStatus,
} from '../composables/useWebSocket'
import ExecutionListItem from './ExecutionListItem.vue'

const props = defineProps<{
  visible: boolean
  workspace?: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const activeTab = ref('active')
const executions = ref<ExecutionStatus[]>([])
const tasks = ref<Record<string, any>>({})
const loading = ref(false)
const error = ref<string | null>(null)

// History tab state
const historyExecutions = ref<HistoryExecution[]>([])
const historyLoading = ref(false)
const historyError = ref<string | null>(null)
const historyPage = ref(1)
const historyPageSize = ref(10)
const historyTotal = ref(0)
const historyTotalPages = ref(0)

// WebSocket management
const { connect, disconnect, isConnectionActive } = useProgressWebSocket()

watch(
  () => props.visible,
  (newVisible, oldVisible) => {
    if (newVisible && !oldVisible) {
      console.log("Open progress panel")
      connect("progressPanel", {
        onTaskProgress: (execution_id: string, progress: any) => {
          tasks.value[execution_id] = progress
        },
        onExecutionProgress: (progress: ExecutionStatus[]) => {
          executions.value = progress
        },
        onExecutionComplete: (_execution_id: string, progress: ExecutionStatus[]) => {
          executions.value = progress
          disconnect("progressPanel")
        },
        onError: (event: Event) => {
          console.error('WebSocket error:', event)
        }
      })
      // Load history when panel opens
      fetchHistory()
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
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to fetch executions'
    console.error('Failed to fetch executions:', err)
  } finally {
    loading.value = false
  }
}

// Fetch history from API
const fetchHistory = async () => {
  if (!props.workspace) {
    historyError.value = 'No workspace configured'
    return
  }
  try {
    historyLoading.value = true
    historyError.value = null
    const response = await getExecutionHistory(props.workspace, historyPage.value, historyPageSize.value)
    historyExecutions.value = response.executions
    historyTotal.value = response.total
    historyTotalPages.value = response.total_pages
  } catch (err) {
    historyError.value = err instanceof Error ? err.message : 'Failed to fetch history'
    console.error('Failed to fetch history:', err)
  } finally {
    historyLoading.value = false
  }
}

// Watch for page changes
watch(historyPage, () => {
  fetchHistory()
})

// Computed property for reversed executions (newer at top)
const reversedExecutions = computed<ExecutionStatus[]>(() => {
  return [...executions.value].reverse()
})

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
        @click="activeTab === 'active' ? fetchExecutions() : fetchHistory()"
        :loading="activeTab === 'active' ? loading : historyLoading"
        title="Refresh"
      >
        <v-icon>mdi-refresh</v-icon>
      </v-btn>
      <v-btn icon variant="text" @click="$emit('update:visible', false)">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-toolbar>

    <v-tabs v-model="activeTab" grow>
      <v-tab value="active">Active</v-tab>
      <v-tab value="history">History</v-tab>
    </v-tabs>

    <v-window v-model="activeTab" class="panel-window">
      <!-- Active Executions Tab -->
      <v-window-item value="active" class="panel-window-item">
        <div class="tab-scroll pa-3">
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

          <!-- Executions list (reversed - newer at top) -->
          <div v-if="executions.length > 0" class="execution-list">
            <ExecutionListItem
              v-for="status in reversedExecutions"
              :key="status.execution_id"
              :execution="status"
              :tasks="tasks[status.execution_id]"
              :is-history="false"
            />
          </div>
        </div>
      </v-window-item>

      <!-- History Tab -->
      <v-window-item value="history" class="panel-window-item">
        <div class="tab-scroll pa-3">
          <!-- Loading state -->
          <div v-if="historyLoading" class="text-center py-4">
            <v-progress-circular indeterminate size="24" class="mr-2" />
            Loading history...
          </div>

          <!-- Error state -->
          <div v-if="historyError" class="text-center py-4">
            <v-alert type="error" variant="tonal" class="mb-2">
              {{ historyError }}
            </v-alert>
            <div class="text-caption">Use the refresh button in the toolbar to retry</div>
          </div>

          <!-- Empty state -->
          <div
            v-if="!historyLoading && !historyError && historyExecutions.length === 0"
            class="text-center py-4 text-grey"
          >
            <v-icon size="48" class="mb-2">mdi-history</v-icon>
            <div>No history found</div>
            <div class="text-caption">Completed executions will appear here</div>
          </div>

          <!-- History list (expandable like active tab) -->
          <div v-if="historyExecutions.length > 0" class="execution-list">
            <ExecutionListItem
              v-for="history in historyExecutions"
              :key="history.execution_id"
              :execution="history"
              :is-history="true"
            />
          </div>

          <!-- Pagination for history -->
          <div v-if="historyExecutions.length > 0" class="d-flex align-center justify-center pa-2">
            <v-pagination
              v-model="historyPage"
              :length="historyTotalPages"
              :total-visible="7"
              density="comfortable"
              size="small"
            />
          </div>
        </div>
      </v-window-item>
    </v-window>
  </v-navigation-drawer>
</template>

<style scoped>
/* Position the panel to the right of the side nav */
:deep(.status-panel) {
  left: 56px !important;
}

:deep(.status-panel .v-navigation-drawer__content) {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-window {
  flex: 1 1 auto;
  min-height: 0;
}

.panel-window-item {
  height: 100%;
}

.tab-scroll {
  height: 100%;
  min-height: 0;
  overflow-y: auto;
}

.execution-list {
  border-top: 1px solid rgba(var(--v-border-color), 0.12);
}
</style>
