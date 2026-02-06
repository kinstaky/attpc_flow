<script setup lang="ts">
import { ref, computed, onMounted, inject } from 'vue'
import { type WorkflowRun } from '../models/workflow'
import { activeWorkspace } from '../models/tabs'
import {
  getTags,
  getRunsInfo,
  refreshRuns,
  type RunInfo
} from '../api/runs'
import {
  parseRunNumbers,
  formatRunNumbers,
  validateRunNumbers,
} from '../utils/runNumbers'

const props = defineProps<{
  runInfo: WorkflowRun
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'apply', value: WorkflowRun): void
}>()

const showError = inject<(message: string) => void>('showError', (msg: string) => {
  console.error('Error (no handler):', msg)
})

// fetch data
const loading = ref(false)
const runsInfo = ref<RunInfo[]>([])
const tagInGroups = ref<Record<string, string[]>>({})
const fetchData = async () => {
  if (!activeWorkspace.value) {
    showError('No workspace selected')
    return
  }

  loading.value = true
  try {
    const [tags, info] = await Promise.all([
      getTags(activeWorkspace.value),
      getRunsInfo(activeWorkspace.value)
    ])
    tagInGroups.value = tags
    runsInfo.value = info
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to fetch run data'
    showError(errorMessage)
  } finally {
    loading.value = false
  }
}

const refreshData = async () => {
  if (!activeWorkspace.value) {
    showError('No workspace selected')
    return
  }

  loading.value = true
  try {
    await refreshRuns(activeWorkspace.value)
    await fetchData()
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to refresh database'
    showError(errorMessage)
  } finally {
    loading.value = false
  }
}

const runs = ref(props.runInfo.runs)
const tags = ref(props.runInfo.tags)

// text input
const runRawString = ref<string>(formatRunNumbers(runs.value))
const runString = computed({
  get: () => formatRunNumbers(runs.value),
  set: (value) => {
    runRawString.value = value
  }
})
const handleRunInputFocus = (focused: boolean) => {
  if (!focused) {
    runs.value = parseRunNumbers(runRawString.value)
  }
}
const runNumberRules = [
  (value: string) => {
    const result = validateRunNumbers(value)
    return result === true ? true : result
  }
]

// select tags
const selectedTags = computed<string[]>({
  get: () => tags.value,
  set: (fullTags: string[]) => {
    tags.value = fullTags
    let tagWithGroup: Record<string, string[]> = {}
    for (const tag of fullTags) {
      const [group, value] = tag.split(':')
      if (group && value) {
        tagWithGroup[group] = tagWithGroup[group] || []
        tagWithGroup[group].push(value)
      }
    }
    runs.value = []
    for (const info of runsInfo.value) {
      // Check if this run matches any of the selected tags
      let matches = 0
      for (const [group, tags] of Object.entries(tagWithGroup)) {
        if (tags.includes(info[group] as string)) {
          matches++
        }
      }
      if (fullTags.length > 0 && matches === Object.keys(tagWithGroup).length) {
        runs.value.push(info.run)
      }
    }
    runRawString.value = formatRunNumbers(runs.value)
  }
})

const getTagColor = (group: string, value: string): string => {
  const tagColor: Record<string, string> = {
    "Half Si": "warning",
    "Normal": "success",
    "Test": "info",
    "Fail": "error",
    "Beam stop": "teal"
  }
  if (value in tagColor) {
    return tagColor[value]
  }
  const colors = [
    'primary', 'success', 'error', 'warning', 'info',
    'purple', 'indigo', 'cyan', 'teal', 'orange', 'brown'
  ]

  let hash = 0
  const str = `${group}:${value}`
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
  }

  return colors[Math.abs(hash) % colors.length]
}

// table
const tableHeaders = computed(() => {
  const headers = [
    { title: 'Run', key: 'run', sortable: true }
  ]

  for (const group of Object.keys(tagInGroups.value)) {
    headers.push({
      title: group.charAt(0).toUpperCase() + group.slice(1),
      key: group,
      sortable: true
    })
  }

  return headers
})

const tableItems = computed(() => {
  console.log(runsInfo.value)
  return runsInfo.value.map(info => {
    const item: any = { run: info["run"] }
    for (const group of Object.keys(tagInGroups.value)) {
      item[group] = info[group]
    }
    return item
  })
})


onMounted(fetchData)
</script>

<template>
  <v-card class="run-sheet">
    <v-card-title class="d-flex align-center pa-4">
      <span>Select Run Numbers</span>
      <v-spacer></v-spacer>
      <v-btn icon variant="text" @click="refreshData" title="Refresh">
        <v-icon>mdi-refresh</v-icon>
      </v-btn>
      <v-btn icon variant="text" @click="$emit('close')" title="Close">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-card-title>

    <v-card-text class="pa-8">
      <v-text-field
        v-model="runString"
        @update:focused="handleRunInputFocus"
        label="Run List"
        variant="outlined"
        density="compact"
        hint="Enter individual numbers separated by commas, or ranges (e.g., 1-5, 8, 10-15)"
        class="flex-grow-1 mr-2"
        :rules="runNumberRules"
      />

      <v-chip-group
        v-model="selectedTags"
        column
        multiple
        class="mb-4"
      >
        <template v-for="(values, group) in tagInGroups" :key="group">
          <v-chip
            v-for="value in values"
            :key="`${group}:${value}`"
            :value="`${group}:${value}`"
            :color="getTagColor(group, value)"
            filter
          >
            {{ group }}: {{ value }}
          </v-chip>
        </template>
      </v-chip-group>

      <v-data-table
        v-model="runs"
        :headers="tableHeaders"
        :items="tableItems"
        item-value="run"
        item-key="run"
        :loading="loading"
        :height="500"
        class="runs-table"
        fixed-header
        show-select
        hide-default-footer
        items-per-page="-1"
        density="compact"
      >
        <template v-for="group in Object.keys(tagInGroups)" v-slot:[`item.${group}`]="{ value }" :key="group">
          <v-chip
            v-if="value"
            size="small"
            :color="getTagColor(group, value)"
            :text="value"
          >
          </v-chip>
        </template>
      </v-data-table>
    </v-card-text>

    <v-card-actions class="pa-4">
      <div class="runs-summary text-caption mb-2">
        {{ runsInfo.length }} runs available, {{ runs.length }} selected
      </div>
      <v-spacer></v-spacer>
      <v-btn @click="$emit('close')">Cancel</v-btn>
      <v-btn color="primary" @click="$emit('apply', {runs: runs, tags: tags})">
        Apply Selection
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<style scoped>
.run-sheet {
  max-height: 80vh;
  width: 80vw;
  overflow-y: auto;
}

.runs-table {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
}

.runs-summary {
  color: rgba(var(--v-theme-on-surface), 0.6);
}
</style>