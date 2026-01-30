/**
 * API Client - TypeScript client for Bot Engine API
 */

import axios, { AxiosInstance } from 'axios'
import type { 
  Session, 
  Stats, 
  BotEvent, 
  HealthCheck, 
  PaginatedSessions, 
  PaginatedEvents,
  SessionFilters 
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_KEY = import.meta.env.VITE_API_KEY || ''

class ApiClient {
  private client: AxiosInstance

  constructor(baseURL: string = API_BASE_URL) {
    this.client = axios.create({
      baseURL,
      timeout: 10000,
      headers: API_KEY ? { 'X-API-Key': API_KEY } : {}
    })
  }

  async healthCheck(): Promise<HealthCheck> {
    const response = await this.client.get('/api/health')
    return response.data
  }

  async getSessions(filters: SessionFilters = { page: 1, per_page: 20 }): Promise<PaginatedSessions> {
    const params = new URLSearchParams()
    params.append('page', filters.page.toString())
    params.append('per_page', filters.per_page.toString())
    
    if (filters.status) params.append('status', filters.status)
    if (filters.country) params.append('country', filters.country)
    if (filters.search) params.append('search', filters.search)

    const response = await this.client.get(`/api/sessions?${params.toString()}`)
    return response.data
  }

  async getSessionsSimple(limit: number = 50): Promise<Session[]> {
    const response = await this.client.get(`/api/sessions?per_page=${limit}`)
    return response.data.sessions || []
  }

  async getSessionDetail(sessionId: string): Promise<{ session: Session; events: BotEvent[]; event_count: number }> {
    const response = await this.client.get(`/api/sessions/${sessionId}`)
    return response.data
  }

  async getStats(): Promise<Stats | null> {
    try {
      const response = await this.client.get('/api/stats')
      return response.data
    } catch (error) {
      console.warn('Failed to fetch stats:', error)
      return null
    }
  }

  async getEvents(page: number = 1, perPage: number = 50, eventType?: string, sessionId?: string): Promise<PaginatedEvents> {
    const params = new URLSearchParams()
    params.append('page', page.toString())
    params.append('per_page', perPage.toString())
    
    if (eventType) params.append('event_type', eventType)
    if (sessionId) params.append('session_id', sessionId)

    const response = await this.client.get(`/api/events?${params.toString()}`)
    return response.data
  }

  async getEventsSimple(limit: number = 200, eventType?: string): Promise<BotEvent[]> {
    const params = new URLSearchParams()
    params.append('per_page', limit.toString())
    if (eventType) params.append('event_type', eventType)

    const response = await this.client.get(`/api/events?${params.toString()}`)
    return response.data.events || []
  }

  async getIPStatus(): Promise<{ proxies: any[]; health: { healthy: number; flagged: number; blacklisted: number } }> {
    const response = await this.client.get('/api/ip/status')
    return response.data
  }

  // Export methods - fetch with auth and trigger download
  async exportSessions(filters?: { status?: string; country?: string }): Promise<void> {
    const params = new URLSearchParams()
    if (filters?.status) params.append('status', filters.status)
    if (filters?.country) params.append('country', filters.country)
    const queryString = params.toString()
    const url = `/api/sessions/export${queryString ? '?' + queryString : ''}`
    
    const response = await this.client.get(url, { responseType: 'blob' })
    this.downloadBlob(response.data, `sessions_${this.getTimestamp()}.csv`)
  }

  async exportEvents(filters?: { event_type?: string; session_id?: string }): Promise<void> {
    const params = new URLSearchParams()
    if (filters?.event_type) params.append('event_type', filters.event_type)
    if (filters?.session_id) params.append('session_id', filters.session_id)
    const queryString = params.toString()
    const url = `/api/events/export${queryString ? '?' + queryString : ''}`
    
    const response = await this.client.get(url, { responseType: 'blob' })
    this.downloadBlob(response.data, `events_${this.getTimestamp()}.csv`)
  }

  private downloadBlob(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }

  private getTimestamp(): string {
    const now = new Date()
    return now.toISOString().slice(0, 19).replace(/[-:T]/g, '')
  }
}

export const apiClient = new ApiClient()
