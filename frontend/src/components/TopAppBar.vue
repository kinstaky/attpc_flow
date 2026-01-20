<script setup lang="ts">
import {
  activeTabId,
  tabs,
  setActiveTab,
  isTabAttached,
  getTabName,
  addNewTab,
  deleteTab as deleteTabFromStore,
  handleDragStart,
  handleDragOver,
  handleDrop,
  handleDragEnd
} from '../stores/tabs'

// Local methods
const handleTabSwitch = (newTabId: string, event?: MouseEvent) => {
  setActiveTab(newTabId)
}

const deleteTab = (tabId: string, event: MouseEvent) => {
  event.stopPropagation()
  // Can only delete the selected tab
  if (activeTabId.value !== tabId) {
    return
  }
  deleteTabFromStore(tabId)
}
</script>

<template>
  <v-app-bar elevation="1" class="top-bar">
    <!-- Left side: Title, Tabs, New Tab, Edit -->
    <div class="d-flex align-center flex-grow-1">
      <span class="text-h6 mr-8">ATTPC Flow</span>

      <!-- Workflow Tabs -->
      <div class="d-flex align-center">
        <v-tabs
          v-model="activeTabId"
          density="compact"
          hide-slider
          class="workflow-tabs"
        >
          <v-tab
            v-for="tab in tabs"
            :key="tab.id"
            :value="tab.id"
            class="custom-tab"
            draggable="true"
            @click="handleTabSwitch(tab.id, $event)"
            @dragstart="handleDragStart($event, tab.id)"
            @dragover="handleDragOver"
            @drop="handleDrop($event, tab.id)"
            @dragend="handleDragEnd"
          >
            <div class="d-flex align-center ga-2">
              <span>{{ getTabName(tab.id) }}</span>
              <span
                v-if="!isTabAttached(tab.id)"
                class="unsaved-indicator"
                title="Not saved to file"
              >•</span>
              <v-btn
                icon="mdi-close"
                variant="text"
                size="x-small"
                v-if="activeTabId === tab.id"
                @click="deleteTab(tab.id, $event)"
                class="ml-0.5 tab-delete-btn"
              ></v-btn>
            </div>
          </v-tab>
        </v-tabs>

        <!-- Add new tab button -->
        <v-btn
          icon="mdi-plus"
          size="small"
          variant="text"
          class="ml-2"
          @click="addNewTab"
        >
        </v-btn>
      </div>
    </div>

    <!-- Right side: Edit button -->
    <v-btn variant="text" size="small">
      <v-icon start>mdi-pencil-outline</v-icon>
      Edit
    </v-btn>
  </v-app-bar>
</template>

<style scoped>
.top-bar {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

/* Custom tab styles - responsive */
:deep(.custom-tab) {
  min-width: auto;
  padding: 0 1rem 0 1rem;
  text-transform: none;
  border-bottom: 2px solid transparent;
  transition: all 0.2s ease;
  cursor: pointer;
  position: relative;
  font-size: 1.0rem;
}

:deep(.custom-tab.v-tab--selected) {
  color: rgb(var(--v-theme-primary));
  border-bottom-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.08);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
  border-radius: 4px 4px 0 0;
  font-size: 1.0rem;
  font-weight: 500;
  padding-right: 0.25rem !important;
}

:deep(.custom-tab:hover) {
  background-color: rgba(var(--v-theme-surface-variant), 0.4);
}

:deep(.custom-tab.v-tab--selected:hover) {
  background-color: rgba(var(--v-theme-primary), 0.12);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  transform: translateY(-3px);
}

/* Unsaved tab indicator */
.unsaved-indicator {
  color: #ff9800;
  font-size: 1.2rem;
  margin-left: 4px;
  opacity: 0.8;
}

/* Tab delete button - always visible when tab is selected */
:deep(.tab-delete-btn) {
  opacity: 1;
  transition: opacity 0.2s ease;
}

:deep(.tab-delete-btn:hover) {
  color: #ff5252 !important;
  background-color: rgba(255, 82, 82, 0.1) !important;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  :deep(.custom-tab) {
    padding: 0 0.125rem 0 0.75rem;
  }
}

@media (max-width: 480px) {
  /* Hide title on small screens */
  .text-h6.mr-8 {
    display: none;
  }

  /* Adjust tab spacing */
  :deep(.custom-tab) {
    padding: 0 0.125rem 0 0.5rem;
    font-size: 0.875rem;
  }
}
</style>
