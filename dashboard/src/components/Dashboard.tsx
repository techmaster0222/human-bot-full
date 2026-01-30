import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '../services/api'
import { wsService } from '../services/websocket'
import { useTheme } from '../context/ThemeContext'
import type { Stats, BotEvent, PaginatedSessions, SessionFilters } from '../types'
import StatsCards from './StatsCards'
import SessionList from './SessionList'
import IPStatus from './IPStatus'
import ActivityChart from './ActivityChart'
import './Dashboard.css'

export default function Dashboard() {
  const { theme, toggleTheme } = useTheme()
  const [stats, setStats] = useState<Stats | null>(null)
  const [sessionsData, setSessionsData] = useState<PaginatedSessions | null>(null)
  const [sessionFilters, setSessionFilters] = useState<SessionFilters>({ page: 1, per_page: 20 })
  const [events, setEvents] = useState<BotEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const [apiConnected, setApiConnected] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [authEnabled, setAuthEnabled] = useState(false)

  const loadSessions = useCallback(async (filters: SessionFilters) => {
    setSessionsLoading(true)
    try {
      const data = await apiClient.getSessions(filters)
      setSessionsData(data)
    } catch (error) {
      console.error('Error loading sessions:', error)
    } finally {
      setSessionsLoading(false)
    }
  }, [])

  const loadData = useCallback(async () => {
    try {
      // Check API health first
      try {
        const health = await apiClient.healthCheck()
        setApiConnected(true)
        setAuthEnabled(health.auth_enabled)
      } catch {
        setApiConnected(false)
        setLoading(false)
        return
      }

      // Load stats and events
      const [statsData, eventsData] = await Promise.all([
        apiClient.getStats(),
        apiClient.getEventsSimple(200)
      ])
      
      setStats(statsData)
      
      // Merge historical events with WebSocket events
      setEvents((prev) => {
        const wsEventIds = new Set(prev.map(e => `${e.type}-${e.timestamp}`))
        const historical = eventsData.filter((e: BotEvent) => 
          !wsEventIds.has(`${e.type}-${e.timestamp}`)
        )
        return [...historical, ...prev].slice(-100)
      })
      
      setLastUpdated(new Date())
      setLoading(false)
    } catch (error) {
      console.error('Error loading data:', error)
      setStats(null)
      setLoading(false)
      setApiConnected(false)
    }
  }, [])

  // Load sessions when filters change
  useEffect(() => {
    if (apiConnected) {
      loadSessions(sessionFilters)
    }
  }, [sessionFilters, apiConnected, loadSessions])

  const handleFilterChange = useCallback((filters: { status?: string; country?: string; search?: string; page?: number }) => {
    setSessionFilters(prev => ({
      ...prev,
      status: filters.status !== undefined ? (filters.status as '' | 'active' | 'completed' | 'failed') : prev.status,
      country: filters.country !== undefined ? filters.country : prev.country,
      search: filters.search !== undefined ? filters.search : prev.search,
      page: filters.page !== undefined ? filters.page : prev.page
    }))
  }, [])

  // Initial load and polling
  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [loadData])

  // WebSocket subscription
  useEffect(() => {
    const unsubscribe = wsService.subscribe((event) => {
      setEvents((prev) => [...prev.slice(-99), event])
      // Refresh stats on new event
      loadData()
      // Refresh sessions if it's a session event
      if (event.type === 'session_start' || event.type === 'session_end') {
        loadSessions(sessionFilters)
      }
    })

    const statusInterval = setInterval(() => {
      setWsConnected(wsService.isConnected())
    }, 1000)

    return () => {
      unsubscribe()
      clearInterval(statusInterval)
    }
  }, [loadData, loadSessions, sessionFilters])

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    )
  }

  return (
    <div className="dashboard">
      {/* Header with theme toggle */}
      <div className="dashboard-header">
        <div className="dashboard-status">
          <div className={`status-indicator ${apiConnected ? 'connected' : 'disconnected'}`}>
            <span className="status-dot"></span>
            {apiConnected ? 'API Connected' : 'API Disconnected'}
          </div>
          <div className={`status-indicator ${wsConnected ? 'connected' : 'disconnected'}`}>
            <span className="status-dot"></span>
            {wsConnected ? 'WebSocket Live' : 'WebSocket Disconnected'}
          </div>
          {authEnabled && (
            <div className="status-indicator auth">
              <span className="status-dot"></span>
              Auth Enabled
            </div>
          )}
          {lastUpdated && (
            <div className="last-updated">
              Updated: {lastUpdated.toLocaleTimeString()}
            </div>
          )}
        </div>
        
        <button 
          className="theme-toggle" 
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      </div>

      {/* API Warning */}
      {!apiConnected && (
        <div className="api-warning">
          <p>⚠️ API server not running. Please start it with:</p>
          <code>cd /opt/project/ads_project && python -m src.api.server</code>
        </div>
      )}

      {/* Main Content */}
      <div className="dashboard-content">
        <div className="dashboard-section">
          <StatsCards stats={stats} />
        </div>

        <div className="dashboard-section">
          <ActivityChart events={events} />
        </div>

        <div className="dashboard-grid">
          <div className="dashboard-section">
            <SessionList 
              sessionsData={sessionsData}
              onFilterChange={handleFilterChange}
              loading={sessionsLoading}
            />
          </div>
          <div className="dashboard-section">
            <IPStatus stats={stats} />
          </div>
        </div>
      </div>
    </div>
  )
}
