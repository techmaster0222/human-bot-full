/**
 * WebSocket Service - Real-time event streaming
 */

import type { BotEvent } from '../types'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

export class WebSocketService {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private reconnectTimeout: number | null = null
  private listeners: Set<(event: BotEvent) => void> = new Set()
  private connected = false
  private connecting = false

  connect(): void {
    if (this.connecting || this.connected) {
      return
    }

    this.connecting = true

    try {
      console.log('WebSocket connecting to:', WS_URL)
      this.ws = new WebSocket(WS_URL)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.connected = true
        this.connecting = false
        this.reconnectAttempts = 0
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          if (message.type === 'event' && message.data) {
            const botEvent: BotEvent = {
              type: message.data.type,
              timestamp: message.data.timestamp || new Date().toISOString(),
              session_id: message.data.data?.session_id,
              data: message.data.data || {}
            }
            this.notifyListeners(botEvent)
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.connected = false
        this.connecting = false
      }

      this.ws.onclose = () => {
        console.log('WebSocket disconnected')
        this.connected = false
        this.connecting = false
        this.reconnect()
      }
    } catch (error) {
      console.error('Error creating WebSocket:', error)
      this.connected = false
      this.connecting = false
      this.reconnect()
    }
  }

  private reconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      // Exponential backoff: 1s, 2s, 4s, 8s, ... up to 30s
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 30000)
      console.log(`WebSocket reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)
      
      this.reconnectTimeout = window.setTimeout(() => {
        this.connect()
      }, delay)
    } else {
      console.log('Max WebSocket reconnection attempts reached')
    }
  }

  subscribe(listener: (event: BotEvent) => void): () => void {
    this.listeners.add(listener)
    return () => {
      this.listeners.delete(listener)
    }
  }

  private notifyListeners(event: BotEvent): void {
    this.listeners.forEach(listener => {
      try {
        listener(event)
      } catch (error) {
        console.error('Error in WebSocket listener:', error)
      }
    })
  }

  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.connected = false
    this.connecting = false
  }

  isConnected(): boolean {
    return this.connected
  }

  // Send a ping to keep connection alive
  ping(): void {
    if (this.ws && this.connected) {
      this.ws.send(JSON.stringify({ type: 'ping' }))
    }
  }
}

export const wsService = new WebSocketService()
