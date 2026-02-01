import { ref, onUnmounted } from 'vue'

export interface ExecutionStatus {
  execution_id: string
  workflow_id: string
  status: 'waiting' | 'running' | 'completed' | 'failed'
  started_at: number | null
  completed_at: number | null
  completed_tasks: number
  total_tasks: number
}

export interface TaskProgress {
  task_id: string
  task_name: string | null
  run: string | null
  percentage: number
  timestamp: number
  status: "running" | "failed" | "completed"
}

export interface WebSocketProgressCallbacks {
  onTaskProgress?: (execution_id: string, progress: Record<string, TaskProgress>) => void
  onExecutionProgress?: (progress: Array<ExecutionStatus>) => void
  onExecutionComplete?: (execution_id: string, progress: Array<ExecutionStatus>) => void
  onError?: (error: Event) => void
}

// Generic WebSocket core function type
export type WebSocketCore<TCallbacks> = (
  callbacks: TCallbacks
) => WebSocket

// Generic WebSocket composable
export function useWebSocket<TCallbacks>(
  createConnection: WebSocketCore<TCallbacks>
) {
  const websockets = ref<Record<string, WebSocket>>({})
  const isConnected = ref<Record<string, boolean>>({})

  const connect = (
    id: string,
    callbacks: TCallbacks
  ) => {
    // Disconnect existing connection if any
    disconnect(id)

    try {
      const ws = createConnection(callbacks)

      websockets.value[id] = ws
      isConnected.value[id] = true

      console.log(`WebSocket connected for id ${id}`)
      return ws
    } catch (error) {
      console.error(`Failed to connect WebSocket for id ${id}:`, error)
      return null
    }
  }

  const disconnect = (id: string) => {
    const ws = websockets.value[id]
    if (ws) {
      ws.close()
      delete websockets.value[id]
      delete isConnected.value[id]
      console.log(`WebSocket disconnected for id ${id}`)
    }
  }

  const disconnectAll = () => {
    Object.keys(websockets.value).forEach(id => {
      disconnect(id)
    })
  }

  const isConnectionActive = (id: string) => {
    return isConnected.value[id] || false
  }

  // Cleanup on unmount
  onUnmounted(() => {
    disconnectAll()
  })

  return {
    websockets: websockets.value,
    isConnected: isConnected.value,
    connect,
    disconnect,
    disconnectAll,
    isConnectionActive
  }
}

// Progress-specific WebSocket core
const connectProgressWebSocket: WebSocketCore<WebSocketProgressCallbacks> = (
  callbacks
) => {
  // Use current host with auto protocol detection
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/ws/progress`

  const ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log(`Connected to progress WebSocket at ${wsUrl}.`)
  }

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    console.log('Received progress data:', data)
    if (data.type === 'task') {
      callbacks.onTaskProgress?.(data.execution_id, data.tasks)
    } else if (data.type === 'execution') {
      callbacks.onExecutionProgress?.(data.executions)
    } else if (data.type === 'execution_complete') {
      callbacks.onExecutionComplete?.(data.execution_id, data.executions)
    }
  }

  ws.onerror = (event: Event) => {
    console.error('WebSocket error:', event)
    callbacks.onError?.(event)
  }

  ws.onclose = () => {
    console.log('WebSocket connection closed')
  }

  return ws
}

// Progress-specific WebSocket composable
export function useProgressWebSocket() {
  return useWebSocket(connectProgressWebSocket)
}

// Singleton instance for global WebSocket management
let globalProgressWebSocketInstance: ReturnType<typeof useProgressWebSocket> | null = null

export function useGlobalProgressWebSocket() {
  if (!globalProgressWebSocketInstance) {
    globalProgressWebSocketInstance = useProgressWebSocket()
  }
  return globalProgressWebSocketInstance
}
