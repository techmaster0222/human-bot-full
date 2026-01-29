import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_KEY = import.meta.env.VITE_API_KEY || ''

const api = axios.create({
  baseURL: API_URL,
  headers: { 'X-API-Key': API_KEY }
})

export const apiClient = {
  getHealth: () => api.get('/api/health'),
  getSessions: (params?: Record<string, string>) => api.get('/api/sessions', { params }),
  getEvents: (params?: Record<string, string>) => api.get('/api/events', { params }),
  getStats: () => api.get('/api/stats'),
  getIPStatus: () => api.get('/api/ip/status'),
  exportSessions: async () => {
    const response = await api.get('/api/sessions/export', { responseType: 'blob' })
    const url = window.URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'sessions.csv'
    a.click()
  }
}

export default apiClient
