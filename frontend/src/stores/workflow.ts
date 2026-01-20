import { reactive, toRefs } from 'vue'

// Reactive state store - only shared state that needs to be accessed across components
export const workflowState = reactive({
  // Active tab state - shared between TopAppBar and FloatingButtons
  activeTabId: 'tab1',
  activeTabName: 'untitled',

  // Methods
  setActiveTab(tabId: string, tabName: string) {
    this.activeTabId = tabId
    this.activeTabName = tabName
  },

  updateActiveTabName(name: string) {
    this.activeTabName = name
  }
})

// Export reactive refs for direct access
export const { activeTabId, activeTabName } = toRefs(workflowState)
