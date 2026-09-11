import { onBeforeUnmount, ref, watch, type Ref } from 'vue'
import { API_BASE_URL, tokenStorage } from '@/api/http'
import type { WsEvent } from '@/types/api'

const RECONNECT_DELAYS = [1000, 2000, 5000, 10000, 15000]

function socketUrl(projectId: number): string {
  const token = encodeURIComponent(tokenStorage.access ?? '')
  const base = /^https?:\/\//.test(API_BASE_URL)
    ? API_BASE_URL.replace(/^http/, 'ws')
    : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}${API_BASE_URL}`
  return `${base.replace(/\/$/, '')}/ws/projects/${projectId}?token=${token}`
}

export function useProjectSocket(projectId: Ref<number | null>, onEvent: (event: WsEvent) => void) {
  const connected = ref(false)
  let socket: WebSocket | null = null
  let pingTimer: ReturnType<typeof setInterval> | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let attempt = 0
  let closedByUs = false

  function cleanup(): void {
    if (pingTimer) clearInterval(pingTimer)
    if (reconnectTimer) clearTimeout(reconnectTimer)
    pingTimer = null
    reconnectTimer = null
    if (socket) {
      closedByUs = true
      socket.onclose = null
      socket.close()
      socket = null
    }
    connected.value = false
  }

  function connect(id: number): void {
    closedByUs = false
    try {
      socket = new WebSocket(socketUrl(id))
    } catch {
      return
    }

    socket.onopen = () => {
      connected.value = true
      attempt = 0
      pingTimer = setInterval(() => {
        if (socket?.readyState === WebSocket.OPEN) socket.send('ping')
      }, 25000)
    }

    socket.onmessage = (message) => {
      try {
        const data = JSON.parse(message.data) as WsEvent
        if (data.type === 'pong' || data.type === 'connected') return
        onEvent(data)
      } catch {
      }
    }

    socket.onclose = (event) => {
      connected.value = false
      if (pingTimer) clearInterval(pingTimer)
      pingTimer = null
      if (closedByUs || projectId.value !== id) return
      if (event.code === 1008) return
      const delay = RECONNECT_DELAYS[Math.min(attempt, RECONNECT_DELAYS.length - 1)]
      attempt += 1
      reconnectTimer = setTimeout(() => connect(id), delay)
    }
  }

  watch(
    projectId,
    (id) => {
      cleanup()
      attempt = 0
      if (id !== null && tokenStorage.access) connect(id)
    },
    { immediate: true },
  )

  onBeforeUnmount(cleanup)

  return { connected }
}
