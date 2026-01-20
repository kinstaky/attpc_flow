import { reactive, computed } from 'vue'

// Tab state enum (internal use only)
enum TabState {
  UNATTACHED = 'unattached',
  ATTACHED_SAVED = 'attached_saved',
  ATTACHED_UNSAVED = 'attached_unsaved' // Not used yet but prepared for future
}

// Tab interface
interface Tab {
  id: string
  name: string | null
  state: TabState
}

// Tab store state
interface TabsStoreState {
  tabs: Tab[]
  activeTabId: string
}

const tabState = reactive<TabsStoreState>({
  tabs: [
    { id: 'tab1', name: null, state: TabState.UNATTACHED }
  ],
  activeTabId: 'tab1'
})

let tabCounter = 1

// Computed properties
export const activeTabId = computed(() => tabState.activeTabId)
export const tabs = computed(() => tabState.tabs)
export const activeTab = computed(() => tabState.tabs.find(t => t.id === tabState.activeTabId))
export const activeTabName = computed(() => activeTab.value?.name || null)

// Tab management functions
export const setActiveTab = (tabId: string) => {
  tabState.activeTabId = tabId
}

export const updateActiveTabName = (name: string | null) => {
  const tab = activeTab.value
  if (tab) {
    tab.name = name
    // If tab is attached and name changes, mark as unsaved
    if (tab.state === TabState.ATTACHED_SAVED && name !== null) {
      tab.state = TabState.ATTACHED_UNSAVED
    }
  }
}

export const addNewTab = () => {
  tabCounter++
  const newTab: Tab = {
    id: `tab${tabCounter}`,
    name: null,
    state: TabState.UNATTACHED
  }
  tabState.tabs.push(newTab)
  setActiveTab(newTab.id)
}

export const deleteTab = (tabId: string) => {
  if (tabState.tabs.length > 1) {
    const index = tabState.tabs.findIndex(t => t.id === tabId)
    if (index !== -1) {
      tabState.tabs.splice(index, 1)
      // Select adjacent tab
      if (index >= tabState.tabs.length) {
        const lastTab = tabState.tabs[tabState.tabs.length - 1]
        if (lastTab) {
          setActiveTab(lastTab.id)
        }
      } else {
        const nextTab = tabState.tabs[index]
        if (nextTab) {
          setActiveTab(nextTab.id)
        }
      }
    }
  }
}

export const getTabName = (tabId: string): string => {
  const tab = tabState.tabs.find(t => t.id === tabId)
  return tab?.name || 'untitled'
}

export const isTabNameUsed = (name: string, excludeTabId?: string): boolean => {
  return tabState.tabs.some(tab =>
    tab.name === name && tab.id !== excludeTabId
  )
}

export const getOtherTabNames = (): string[] => {
  return tabState.tabs
    .filter(tab => tab.id !== tabState.activeTabId && tab.name !== null)
    .map(tab => tab.name!)
}

// Attachment functions
export const attachTab = (tabId: string) => {
  const tab = tabState.tabs.find(t => t.id === tabId)
  if (tab) {
    tab.state = TabState.ATTACHED_SAVED
  }
}

export const isTabAttached = (tabId: string): boolean => {
  const tab = tabState.tabs.find(t => t.id === tabId)
  return tab?.state !== TabState.UNATTACHED || false
}

// Drag and drop handlers
const draggedTab = reactive<{ value: string | null }>({ value: null })

export const handleDragStart = (event: DragEvent, tabId: string) => {
  draggedTab.value = tabId
  event.dataTransfer?.setData('text/plain', tabId)
}

export const handleDragOver = (event: DragEvent) => {
  event.preventDefault()
}

export const handleDrop = (event: DragEvent, targetTabId: string) => {
  event.preventDefault()
  if (draggedTab.value && draggedTab.value !== targetTabId) {
    const draggedIndex = tabState.tabs.findIndex(t => t.id === draggedTab.value)
    const targetIndex = tabState.tabs.findIndex(t => t.id === targetTabId)

    if (draggedIndex !== -1 && targetIndex !== -1) {
      const [draggedItem] = tabState.tabs.splice(draggedIndex, 1)
      if (draggedItem) {
        tabState.tabs.splice(targetIndex, 0, draggedItem)
      }
    }
  }
  draggedTab.value = null
}

export const handleDragEnd = () => {
  draggedTab.value = null
}
