<script setup lang="ts">
import { ref } from 'vue'
import { useTheme } from 'vuetify'

const theme = useTheme()
const isDark = ref(true)

const toggleTheme = () => {
  isDark.value = !isDark.value
  theme.global.name.value = isDark.value ? 'dark' : 'light'
}

const openNodesLibrary = () => {
  // Placeholder for nodes library popup
  console.log('Open nodes library')
}

const openWorkflows = () => {
  // Placeholder for workflows popup
  console.log('Open workflows')
}

const openSettings = () => {
  // Placeholder for settings
  console.log('Open settings')
}
</script>

<template>
  <v-navigation-drawer
    permanent
    width="56"
    color="surface"
    class="side-nav"
  >
    <div class="d-flex flex-column h-100">
      <!-- Top section with icon buttons -->
      <div class="pa-2">
        <v-btn
          icon
          variant="text"
          size="default"
          class="mb-2"
          @click="openNodesLibrary"
        >
          <v-icon>mdi-shape-outline</v-icon>
          <v-tooltip activator="parent" location="end">Nodes Library</v-tooltip>
        </v-btn>

        <v-btn
          icon
          variant="text"
          size="default"
          @click="openWorkflows"
        >
          <v-icon>mdi-folder-open-outline</v-icon>
          <v-tooltip activator="parent" location="end">Workflows</v-tooltip>
        </v-btn>
      </div>

      <v-spacer></v-spacer>

      <!-- Bottom section with controls -->
      <div class="pa-2">
        <v-btn
          icon
          variant="text"
          size="default"
          class="mb-2"
          @click="toggleTheme"
        >
          <v-icon>{{ isDark ? 'mdi-brightness-4' : 'mdi-brightness-6' }}</v-icon>
          <v-tooltip activator="parent" location="end">
            {{ isDark ? 'Switch to Light' : 'Switch to Dark' }}
          </v-tooltip>
        </v-btn>

        <v-btn
          icon
          variant="text"
          size="default"
          @click="openSettings"
        >
          <v-icon>mdi-cog</v-icon>
          <v-tooltip activator="parent" location="end">Settings</v-tooltip>
        </v-btn>
      </div>
    </div>
  </v-navigation-drawer>
</template>

<style scoped>
.side-nav {
  border-right: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

/* Change ripple effect to rounded rectangle */
:deep(.v-btn--variant-text .v-btn__overlay) {
  border-radius: 8px;
}

:deep(.v-btn--variant-text .v-ripple__container) {
  border-radius: 8px;
}
</style>
