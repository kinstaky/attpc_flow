<script setup lang="ts">
import { ref, provide } from 'vue'
import TopAppBar from './TopAppBar.vue'
import SideNav from './SideNav.vue'
import FloatingButtons from './FloatingButtons.vue'
import FlowCanvas from './FlowCanvas.vue'

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
      <!-- Flow Canvas Component -->
      <FlowCanvas />

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

/* Responsive adjustments for canvas */
@media (max-width: 480px) {
  .canvas-container {
    padding-left: 48px; /* Smaller side nav on mobile */
  }
}
</style>
