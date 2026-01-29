import { useState, useEffect } from 'react'
import { apiClient } from '../services'
import { useTheme } from '../context/ThemeContext'
import type { Stats, Session } from '../types'
import './Dashboard.css'

export default function Dashboard() {
  const { theme, toggleTheme } = useTheme()
  const [stats, setStats] = useState<Stats | null>(null)
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, sessionsRes] = await Promise.all([
          apiClient.getStats(),
          apiClient.getSessions()
        ])
        setStats(statsRes.data)
        setSessions(sessionsRes.data.sessions || [])
      } catch (error) {
        console.error('Failed to fetch data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div className="loading">Loading...</div>

  return (
    <div className="dashboard">
      <header className="header">
        <h1>AdsPower Bot Dashboard</h1>
        <button onClick={toggleTheme}>
          {theme === 'light' ? '🌙' : '☀️'}
        </button>
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Sessions</h3>
          <p className="stat-value">{stats?.total_sessions || 0}</p>
        </div>
        <div className="stat-card">
          <h3>Active Sessions</h3>
          <p className="stat-value active">{stats?.active_sessions || 0}</p>
        </div>
        <div className="stat-card">
          <h3>Success Rate</h3>
          <p className="stat-value">{stats?.success_rate?.toFixed(1) || 0}%</p>
        </div>
        <div className="stat-card">
          <h3>IP Health</h3>
          <p className="stat-value healthy">{stats?.ip_health?.healthy || 0}</p>
        </div>
      </div>

      <div className="sessions-list">
        <h2>Recent Sessions</h2>
        <table>
          <thead>
            <tr>
              <th>Profile</th>
              <th>Country</th>
              <th>Status</th>
              <th>Proxy</th>
            </tr>
          </thead>
          <tbody>
            {sessions.slice(0, 10).map(session => (
              <tr key={session.id}>
                <td>{session.profile_id}</td>
                <td>{session.country}</td>
                <td className={`status-${session.status}`}>{session.status}</td>
                <td>{session.proxy}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
