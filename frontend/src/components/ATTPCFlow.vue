<script setup lang="ts">
import { onMounted } from 'vue'
import TopAppBar from './TopAppBar.vue'
import SideNav from './SideNav.vue'
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
  padding-left: 56px; /* Account for side nav width */
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
</style>
