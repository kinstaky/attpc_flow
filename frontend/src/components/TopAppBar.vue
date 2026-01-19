<script setup lang="ts">
import { ref } from 'vue'

const activeTab = ref('tab1')
const workspaceInput = ref('')

const workflowTabs = ref([
  { id: 'tab1', name: 'Default' },
  { id: 'tab2', name: 'Workflow 2' },
  { id: 'tab3', name: 'Workflow 3' },
])

const addNewTab = () => {
  // Placeholder for adding new tab functionality
  console.log('Add new tab')
}
</script>

<template>
  <v-app-bar elevation="0" height="48" class="top-bar">
    <!-- Left side items -->
    <div class="d-flex align-center ga-4">
      <span class="text-h6 font-weight-bold">ATTPC Flow</span>

      <v-btn variant="text" size="small" class="text-none">
        <span class="ml-1">Workflow</span>
      </v-btn>

      <v-btn variant="text" size="small" class="text-none">
        <span class="ml-1">Edit</span>
      </v-btn>

      <v-btn variant="text" size="small" class="text-none">
        <span class="ml-1">Help</span>
      </v-btn>

      <v-divider vertical class="mx-2"></v-divider>

      <!-- Workflow Tabs -->
      <v-tabs v-model="activeTab" height="32" color="primary" hide-slider>
        <v-tab v-for="tab in workflowTabs" :key="tab.id" :value="tab.id">
          {{ tab.name }}
        </v-tab>
      </v-tabs>

      <!-- Add new tab button -->
      <v-btn
        icon="mdi-plus"
        size="small"
        variant="text"
        class="ml-2"
        @click="addNewTab"
      ></v-btn>
    </div>

    <!-- Right side items -->
    <v-spacer></v-spacer>

    <div class="d-flex align-center ga-2">
      <v-text-field
        v-model="workspaceInput"
        placeholder="Workspace..."
        density="compact"
        variant="outlined"
        hide-details
        style="width: 200px"
      ></v-text-field>

      <v-btn variant="flat" color="primary" size="small">
        <v-icon start>mdi-play</v-icon>
        Run
      </v-btn>

      <v-btn icon size="small" variant="text">
        <v-icon>mdi-menu</v-icon>
      </v-btn>
    </div>
  </v-app-bar>
</template>

<style scoped>
.top-bar {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
