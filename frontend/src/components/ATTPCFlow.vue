<script setup lang="ts">
import { ref } from 'vue'
import TopAppBar from './TopAppBar.vue'
import SideNav from './SideNav.vue'
import FloatingButtons from './FloatingButtons.vue'

const topAppBarRef = ref<InstanceType<typeof TopAppBar>>()

// Handle workflow actions from FloatingButtons
const handleWorkflowAction = (action: string, data?: any) => {
  switch (action) {
    case 'duplicate':
      if (topAppBarRef.value) {
        topAppBarRef.value.addNewTab()
      }
      break
    case 'save':
      console.log('Save workflow:', data)
      // TODO: Implement actual save
      break
    case 'saveAs':
      console.log('Save as workflow')
      // TODO: Implement save as dialog
      break
    case 'rename':
      if (topAppBarRef.value && data) {
        topAppBarRef.value.updateCurrentTabName(data)
      }
      break
    case 'delete':
      console.log('Delete workflow:', data)
      // TODO: Implement actual delete
      break
    case 'run':
      console.log('Run workflow')
      // TODO: Implement run workflow
      break
  }
}
</script>

<template>
  <v-app class="attp-flow">
    <TopAppBar ref="topAppBarRef" />

    <SideNav />

    <!-- Main Canvas Area -->
    <v-main class="canvas-container">
      <div class="canvas-wrapper" @contextmenu.prevent>
        <!-- Vue Flow will be mounted here -->
        <div class="canvas-placeholder">
          <v-icon size="64" color="grey-darken-2">mdi-node</v-icon>
          <p class="text-h6 mt-4 text-grey-darken-2">Canvas Area</p>
          <p class="text-body-2 text-grey-darken-1">Right-click disabled • No scrolling</p>
        </div>
      </div>

      <!-- Floating Buttons Component -->
      <FloatingButtons @workflow-action="handleWorkflowAction" />
    </v-main>
  </v-app>
</template>

<style scoped>
.attp-flow {
  height: 100vh;
  overflow: hidden;
}

.canvas-container {
  position: relative;
  background: #1e1e1e;
  overflow: hidden;
  padding-left: 56px; /* Fixed width for side nav */
}

.canvas-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
}

.canvas-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  opacity: 0.5;
}

/* Responsive adjustments for canvas */
@media (max-width: 480px) {
  .canvas-container {
    padding-left: 48px; /* Smaller side nav on mobile */
  }
}
</style>
