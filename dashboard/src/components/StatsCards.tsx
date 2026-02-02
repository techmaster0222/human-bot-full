import type { Stats } from '../types'
import './StatsCards.css'

// SVG Icons for professional look
const Icons = {
  total: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1"/>
      <rect x="14" y="3" width="7" height="7" rx="1"/>
      <rect x="3" y="14" width="7" height="7" rx="1"/>
      <rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>
  ),
  active: (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <circle cx="12" cy="12" r="8"/>
    </svg>
  ),
  success: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6L9 17l-5-5"/>
    </svg>
  ),
  failed: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 6L6 18M6 6l12 12"/>
    </svg>
  ),
  rate: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18"/>
      <path d="M18 9l-5 5-4-4-3 3"/>
    </svg>
  ),
  duration: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <path d="M12 6v6l4 2"/>
    </svg>
  ),
}

interface StatsCardsProps {
  stats: Stats | null
}

export default function StatsCards({ stats }: StatsCardsProps) {
  if (!stats) {
    return (
      <div className="stats-cards">
        <div className="stat-card empty">
          <div className="stat-icon">{Icons.total}</div>
          <div className="stat-content">
            <div className="stat-value">-</div>
            <div className="stat-label">No data available</div>
            <div className="stat-hint">Start the API server to see statistics</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="stats-cards">
      <div className="stat-card total">
        <div className="stat-icon">{Icons.total}</div>
        <div className="stat-content">
          <div className="stat-value">{stats.total_sessions}</div>
          <div className="stat-label">Total Sessions</div>
        </div>
      </div>

      <div className="stat-card active">
        <div className="stat-icon">{Icons.active}</div>
        <div className="stat-content">
          <div className="stat-value">{stats.active_sessions}</div>
          <div className="stat-label">Active Sessions</div>
        </div>
      </div>

      <div className="stat-card success">
        <div className="stat-icon">{Icons.success}</div>
        <div className="stat-content">
          <div className="stat-value">{stats.successful_sessions}</div>
          <div className="stat-label">Successful</div>
        </div>
      </div>

      <div className="stat-card error">
        <div className="stat-icon">{Icons.failed}</div>
        <div className="stat-content">
          <div className="stat-value">{stats.failed_sessions}</div>
          <div className="stat-label">Failed</div>
        </div>
      </div>

      <div className="stat-card rate">
        <div className="stat-icon">{Icons.rate}</div>
        <div className="stat-content">
          <div className="stat-value">{stats.success_rate.toFixed(1)}%</div>
          <div className="stat-label">Success Rate</div>
        </div>
      </div>

      <div className="stat-card duration">
        <div className="stat-icon">{Icons.duration}</div>
        <div className="stat-content">
          <div className="stat-value">{stats.average_duration.toFixed(1)}s</div>
          <div className="stat-label">Avg Duration</div>
        </div>
      </div>
    </div>
  )
}
