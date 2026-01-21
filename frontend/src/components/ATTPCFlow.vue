<script setup lang="ts">
import { ref, provide } from 'vue'
import TopAppBar from './TopAppBar.vue'
import SideNav from './SideNav.vue'
import FloatingButtons from './FloatingButtons.vue'

// Snackbar state
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('error')

// Function to show error messages
const showError = (message: string) => {
  snackbarText.value = message
  snackbarColor.value = 'error'
  snackbar.value = true
}

// Provide error handler to child components
provide('showError', showError)
</script>

<template>
  <v-app class="attp-flow">
    <TopAppBar />

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
      <FloatingButtons />
    </v-main>

    <!-- Error Snackbar -->
    <v-snackbar
      v-model="snackbar"
      :color="snackbarColor"
      :timeout="5000"
      location="bottom"
    >
      {{ snackbarText }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar = false">
          Close
        </v-btn>
      </template>
    </v-snackbar>
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
