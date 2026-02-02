import { reactive, computed } from 'vue'
import { type Node, type Position } from '../types/node'
import { type Link } from '../types/link'
import { Workflow } from '../models/workflow'
import { OperationStack } from './operationStack'
import {
  getWorkflow,
  deleteWorkflow,
  updateWorkflow,
  createWorkflow
} from '../api/workflow'


// Tab interface
interface Tab {
  id: string
  saved: boolean
  workflow: Workflow
  operationStack: OperationStack
}

// Tab store state
interface TabsStoreState {
  tabs: Tab[]
  activeTabId: string | null
}

const tabState = reactive<TabsStoreState>({
  tabs: [] as Tab[],
  activeTabId: null
})


// Computed properties
export const tabs = computed(() => tabState.tabs)
export const activeTabId = computed(() => tabState.activeTabId)
export const activeTab = computed(() => tabState.tabs.find(t => t.id === tabState.activeTabId) ?? null)
export const activeTabSaved = computed(() => activeTab.value?.saved || false)
export const activeTabName = computed(() => activeTab.value?.workflow.name || null)
export const activeWorkflow = computed(() => activeTab.value?.workflow || null)
export const activeWorkspace = computed(() => activeTab.value?.workflow.workspace || null)
export const activeWorkers = computed(() => activeTab.value?.workflow.workers || null)

// Tabs management functions
export const setActiveTab = (tabId: string) => {
  tabState.activeTabId = tabId
}

// Tab management functions
export const createTab = async (workflowName: string) => {
  // console.log(`Create tab with workflow ${workflowName}`)
  if (tabState.tabs.find(t => t.id == workflowName)) {
    setActiveTab(workflowName)
    return
  }
  const workflow = await getWorkflow(workflowName)
  tabState.tabs.push({
    id: workflow.name,
    saved: true,
    workflow: workflow,
    operationStack: new OperationStack()
  })
  setActiveTab(workflow.name)
}

export const closeActiveTab = (save: boolean = false) => {
  if (!activeTab.value) return
  if (save && !activeTab.value.saved) {
    saveActiveTab()
  }
  if (tabState.tabs.length > 1) {
    const index = tabs.value.findIndex(t => t.id === activeTab.value!.id)
    if (index !== -1) {
      tabState.tabs.splice(index, 1)
      setActiveTab(tabs.value[tabs.value.length-1].id)
    }
  } else {
    tabState.tabs = []
    tabState.activeTabId = null
  }
}

export const deleteActiveTab = () => {
  if (!activeTab.value) return
  const workflowName = activeTab.value.workflow.name
  closeActiveTab()
  deleteWorkflow(workflowName)
}

export const saveActiveTab = async () => {
  if (!activeTab.value) return
  if (activeTab.value.saved) return
  const workflow = activeTab.value.workflow
  if (!workflow) return
  updateWorkflow(workflow)
    .then(() => {
      const tab = tabState.tabs.find(t => t.id === activeTab.value!.id)
      if (tab) tab.saved = true
    })
    .catch((error) => {
      console.error(error)
    })
}

export const renameActiveTab = async (name: string) => {
  if (!activeTab.value) return
  if (!activeTab.value.saved) return
  const tab = tabState.tabs.find(t => t.id === activeTab.value!.id)!
  const oldName = tab.workflow.name
  activeWorkflow.value?.changeName(name)
  // tab.workflow.name = name
  try {
    await createWorkflow(tab.workflow)
    await deleteWorkflow(oldName)
  } catch {
    // tab.workflow.name = oldName
    activeWorkflow.value?.changeName(oldName)
  }
}

export const unsaveActiveTab = () => {
  const tab = tabState.tabs.find(t => t.id === activeTab.value!.id)
  if (tab) tab.saved = false
}

export const activeWorkflowAddNode = (node: Node, bind=false) => {
  if (!activeTab.value) return
  const tab = tabState.tabs.find(t => t.id === activeTab.value!.id)
  if (!tab) return
  tab.workflow.pushNode(node)
  tab.operationStack.push({
    redo: {
      call: tab.workflow.pushNode,
      parameters: [node],
    },
    undo: {
      call: tab.workflow.popNode,
      parameters: [],
    },
    bind: bind,
  })
  tab.saved = false
}

export const activeWorkflowDeleteNode = (nodeId: number, bind=false) => {
  if (!activeTab.value) return
  const tab = tabState.tabs.find(t => t.id === activeTab.value!.id)
  if (!tab) return
  const toRemove = tab.workflow.nodes.find(n => n.id == nodeId)
  if (!toRemove) return
  // search for link
  for (const port of toRemove.inputs.concat(toRemove.outputs).concat(toRemove.properties)) {
    for (const linkId of port.links) {
      activeWorkflowRemoveLink(linkId, true)
    }
  }

  const removed = tab.workflow.removeNode(nodeId)
  if (!removed) return
  tab.operationStack.push({
    redo: {
      call: tab.workflow.removeNode,
      parameters: [nodeId]
    },
    undo: {
      call: tab.workflow.insertNode,
      parameters: removed
    },
    bind: bind,
  })
  tab.saved = false
}

export const activeWorkflowMoveNode = (nodeId: number, position: Position, bind=false) => {
  if (!activeTab.value) return
  const tab = tabState.tabs.find(t => t.id === activeTab.value!.id)
  if (!tab) return
  const oldPosition = tab.workflow.moveNode(nodeId, position)
  if (!oldPosition) return
  tab.operationStack.push({
    redo: {
      call: tab.workflow.moveNode,
      parameters: [nodeId, position]
    },
    undo: {
      call: tab.workflow.moveNode,
      parameters: [nodeId, oldPosition]
    },
    bind: bind,
  })
  tab.saved = false
}

export const activeWorkflowAddLink = (link: Link, bind=false) => {
  if (!activeTab.value) return
  const tab = tabState.tabs.find(t => t.id === activeTab.value!.id)
  if (!tab) return
  tab.workflow.pushLink(link)
  tab.operationStack.push({
    redo: {
      call: tab.workflow.pushLink,
      parameters: [link]
    },
    undo: {
      call: tab.workflow.popLink,
      parameters: []
    },
    bind: bind,
  })
  tab.saved = false
}

export const activeWorkflowRemoveLink = (linkId: number, bind=false) => {
  if (!activeTab.value) return
  const tab = tabState.tabs.find(t => t.id === activeTab.value!.id)
  if (!tab) return
  const removed = tab.workflow.removeLink(linkId)
  if (!removed) return
  tab.operationStack.push({
    redo: {
      call: tab.workflow.removeLink,
      parameters: [linkId]
    },
    undo: {
      call: tab.workflow.insertLink,
      parameters: removed
    },
    bind: bind,
  })
  tab.saved = false
}

export const isTabSaved = (tabId: string): boolean => {
  const tab = tabState.tabs.find(t => t.id === tabId)
  return tab?.saved || false
}


// function updateState(tab: Tab) {
//   if (tab.state === TabState.ATTACHED_SAVED) {
//     tab.state = TabState.ATTACHED_UNSAVED
//   }
// }

// export const updateActiveWorkflow = (workflow: Workflow) => {
//   const tab = activeTab.value
//   if (tab) {
//     tab.workflow = workflow
//     updateState(tab)
//   }
// }

// export const setActiveWorkflow = (workflow: Workflow) => {
//   const tab = activeTab.value
//   if (tab) {
//     tab.workflow = workflow
//     updateState(tab)
//   }
// }

// export const addNewTab = () => {
//   tabCounter++
//   const newWorkflow = defaultWorkflow(activeWorkspace.value)
//   const newTab: Tab = {
//     id: `tab${tabCounter}`,
//     state: TabState.UNATTACHED,
//     workflow: newWorkflow,
//   }
//   tabState.tabs.push(newTab)
//   setActiveTab(newTab.id)
// }

// export const deleteTab = (tabId: string) => {
//   if (tabState.tabs.length > 1) {
//     const index = tabState.tabs.findIndex(t => t.id === tabId)
//     if (index !== -1) {
//       tabState.tabs.splice(index, 1)
//       // Select previous tab (to the left), or first tab if deleting the first one
//       if (index > 0) {
//         const prevTab = tabState.tabs[index - 1]
//         if (prevTab) {
//           setActiveTab(prevTab.id)
//         }
//       } else {
//         // If we're deleting the first tab, select the new first tab
//         const firstTab = tabState.tabs[0]
//         if (firstTab) {
//           setActiveTab(firstTab.id)
//         }
//       }
//     }
//   } else if (tabState.tabs.length === 1) {
//     // If this is the only tab, remove it and create a new empty one
//     addNewTab()
//     tabState.tabs.splice(0, 1)
//   }
// }

// export const getTabName = (tabId: string): string => {
//   const tab = tabState.tabs.find(t => t.id === tabId)
//   return tab?.workflow.name || 'untitled'
// }

// export const isTabNameUsed = (name: string, excludeTabId?: string): boolean => {
//   return tabState.tabs.some(tab =>
//     tab.workflow.name === name && tab.id !== excludeTabId
//   )
// }

// export const getOtherTabNames = (): string[] => {
//   return tabState.tabs
//     .filter(tab => tab.id !== tabState.activeTabId && tab.workflow.name !== null)
//     .map(tab => tab.workflow.name!)
// }

// // Attachment functions
// export const saveTab = (tabId: string) => {
//   const tab = tabState.tabs.find(t => t.id === tabId)
//   if (tab) {
//     tab.state = TabState.ATTACHED_SAVED
//   }
// }

// export const isTabAttached = (tabId: string): boolean => {
//   const tab = tabState.tabs.find(t => t.id === tabId)
//   return tab?.state !== TabState.UNATTACHED || false
// }



// export const isTabEmpty = (tabId: string): boolean => {
//   const tab = tabState.tabs.find(t => t.id === tabId)
//   return tab?.workflow.name === null
// }