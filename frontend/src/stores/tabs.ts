import { reactive, computed } from 'vue'
import { defaultWorkflow, type Workflow } from './workflow'

// Tab state enum (internal use only)
enum TabState {
  UNATTACHED = 'unattached',
  ATTACHED_SAVED = 'attached_saved',
  ATTACHED_UNSAVED = 'attached_unsaved' // Not used yet but prepared for future
}

// Tab interface
interface Tab {
  id: string
  state: TabState
  workflow: Workflow
}

// Tab store state
interface TabsStoreState {
  tabs: Tab[]
  activeTabId: string
}

const tabState = reactive<TabsStoreState>({
  tabs: [
    {
      id: 'tab1',
      state: TabState.UNATTACHED,
      workflow: defaultWorkflow()
    }
  ],
  activeTabId: 'tab1'
})

let tabCounter = 1

// Computed properties
export const activeTabId = computed(() => tabState.activeTabId)
export const tabs = computed(() => tabState.tabs)
export const activeTab = computed(() => tabState.tabs.find(t => t.id === tabState.activeTabId) ?? null)
export const activeTabName = computed(() => activeTab.value?.workflow.name || null)
export const activeWorkflow = computed(() => activeTab.value?.workflow || null)
export const activeWorkspace = computed(() => activeTab.value?.workflow.workspace || null)

// Tab management functions
export const setActiveTab = (tabId: string) => {
  tabState.activeTabId = tabId
}

export const updateActiveTabName = (name: string) => {
  if (activeTab.value) {
    activeTab.value.workflow.name = name
  }
}

function updateState(tab: Tab) {
  if (tab.state === TabState.ATTACHED_SAVED) {
    tab.state = TabState.ATTACHED_UNSAVED
  }
}

export const updateActiveWorkflow = (workflow: Workflow) => {
  const tab = activeTab.value
  if (tab) {
    tab.workflow = workflow
    updateState(tab)
  }
}

export const setActiveWorkflow = (workflow: Workflow) => {
  const tab = activeTab.value
  if (tab) {
    tab.workflow = workflow
    updateState(tab)
  }
}

export const addNewTab = () => {
  tabCounter++
  const newWorkflow = defaultWorkflow(activeWorkspace.value)
  const newTab: Tab = {
    id: `tab${tabCounter}`,
    state: TabState.UNATTACHED,
    workflow: newWorkflow,
  }
  tabState.tabs.push(newTab)
  setActiveTab(newTab.id)
}

export const deleteTab = (tabId: string) => {
  if (tabState.tabs.length > 1) {
    const index = tabState.tabs.findIndex(t => t.id === tabId)
    if (index !== -1) {
      tabState.tabs.splice(index, 1)
      // Select previous tab (to the left), or first tab if deleting the first one
      if (index > 0) {
        const prevTab = tabState.tabs[index - 1]
        if (prevTab) {
          setActiveTab(prevTab.id)
        }
      } else {
        // If we're deleting the first tab, select the new first tab
        const firstTab = tabState.tabs[0]
        if (firstTab) {
          setActiveTab(firstTab.id)
        }
      }
    }
  } else if (tabState.tabs.length === 1) {
    // If this is the only tab, remove it and create a new empty one
    addNewTab()
    tabState.tabs.splice(0, 1)
  }
}

export const getTabName = (tabId: string): string => {
  const tab = tabState.tabs.find(t => t.id === tabId)
  return tab?.workflow.name || 'untitled'
}

export const isTabNameUsed = (name: string, excludeTabId?: string): boolean => {
  return tabState.tabs.some(tab =>
    tab.workflow.name === name && tab.id !== excludeTabId
  )
}

export const getOtherTabNames = (): string[] => {
  return tabState.tabs
    .filter(tab => tab.id !== tabState.activeTabId && tab.workflow.name !== null)
    .map(tab => tab.workflow.name!)
}

// Attachment functions
export const saveTab = (tabId: string) => {
  const tab = tabState.tabs.find(t => t.id === tabId)
  if (tab) {
    tab.state = TabState.ATTACHED_SAVED
  }
}

export const isTabAttached = (tabId: string): boolean => {
  const tab = tabState.tabs.find(t => t.id === tabId)
  return tab?.state !== TabState.UNATTACHED || false
}

export const isTabSaved = (tabId: string): boolean => {
  const tab = tabState.tabs.find(t => t.id === tabId)
  return tab?.state === TabState.ATTACHED_SAVED || false
}

export const isTabEmpty = (tabId: string): boolean => {
  const tab = tabState.tabs.find(t => t.id === tabId)
  return tab?.workflow.name === null
}