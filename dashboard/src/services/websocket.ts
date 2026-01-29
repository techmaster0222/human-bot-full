const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

export function createWebSocket(onMessage: (data: unknown) => void) {
  const ws = new WebSocket(WS_URL)
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage(data)
    } catch (e) {
      console.error('WebSocket parse error:', e)
    }
  }
  
  ws.onerror = (error) => console.error('WebSocket error:', error)
  
  return ws
}
