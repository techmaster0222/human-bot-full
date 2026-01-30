import { useState } from 'react'
import type { Session, PaginatedSessions } from '../types'
import { formatDistanceToNow } from 'date-fns'
import { apiClient } from '../services/api'
import './SessionList.css'

interface SessionListProps {
  sessionsData: PaginatedSessions | null
  onFilterChange: (filters: { status?: string; country?: string; search?: string; page?: number }) => void
  loading?: boolean
}

export default function SessionList({ sessionsData, onFilterChange, loading }: SessionListProps) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [countryFilter, setCountryFilter] = useState('')
  const [exporting, setExporting] = useState(false)

  const sessions = sessionsData?.sessions || []
  const totalPages = sessionsData?.total_pages || 1
  const currentPage = sessionsData?.page || 1
  const total = sessionsData?.total || 0

  const handleSearchChange = (value: string) => {
    setSearch(value)
    onFilterChange({ search: value, status: statusFilter, country: countryFilter, page: 1 })
  }

  const handleStatusChange = (value: string) => {
    setStatusFilter(value)
    onFilterChange({ status: value, search, country: countryFilter, page: 1 })
  }

  const handleCountryChange = (value: string) => {
    setCountryFilter(value)
    onFilterChange({ country: value, search, status: statusFilter, page: 1 })
  }

  const handlePageChange = (page: number) => {
    onFilterChange({ page, search, status: statusFilter, country: countryFilter })
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      await apiClient.exportSessions({
        status: statusFilter || undefined,
        country: countryFilter || undefined
      })
    } catch (error) {
      console.error('Export failed:', error)
      alert('Failed to export sessions. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  const getStatusBadge = (session: Session) => {
    if (session.status === 'active') {
      return <span className="status-badge active">● Active</span>
    } else if (session.success) {
      return <span className="status-badge success">✓ Success</span>
    } else {
      return <span className="status-badge failed">✗ Failed</span>
    }
  }

  // Get unique countries from sessions
  const countries = [...new Set(sessions.filter(s => s.country).map(s => s.country!))]

  return (
    <div className="session-list">
      <div className="section-header">
        <h2 className="section-title">Sessions</h2>
        <button 
          className="export-btn" 
          onClick={handleExport} 
          disabled={exporting}
          title="Export to CSV"
        >
          {exporting ? '⏳ Exporting...' : '📥 Export'}
        </button>
      </div>

      {/* Filters */}
      <div className="filters">
        <input
          type="text"
          placeholder="Search session ID, profile, proxy..."
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="search-input"
        />
        
        <select 
          value={statusFilter} 
          onChange={(e) => handleStatusChange(e.target.value)}
          className="filter-select"
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>

        <select 
          value={countryFilter} 
          onChange={(e) => handleCountryChange(e.target.value)}
          className="filter-select"
        >
          <option value="">All Countries</option>
          {countries.map(c => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {/* Results count */}
      <div className="results-count">
        Showing {sessions.length} of {total} sessions
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="spinner small"></div>
          <p>Loading...</p>
        </div>
      ) : sessions.length === 0 ? (
        <div className="empty-state">
          <p>No sessions found</p>
          <p className="hint">
            {search || statusFilter || countryFilter 
              ? 'Try adjusting your filters' 
              : 'Sessions will appear here when the bot runs'}
          </p>
        </div>
      ) : (
        <>
          <div className="session-items">
            {sessions.map((session) => (
              <div key={session.session_id} className={`session-item ${session.status}`}>
                <div className="session-header">
                  <span className="session-id" title={session.session_id}>
                    {session.session_id.substring(0, 8)}...
                  </span>
                  {getStatusBadge(session)}
                </div>
                
                <div className="session-details">
                  <div className="session-detail">
                    <span className="detail-label">Profile:</span>
                    <span className="detail-value">{session.profile_id || '-'}</span>
                  </div>
                  
                  <div className="session-detail">
                    <span className="detail-label">Device:</span>
                    <span className="detail-value">{session.device}</span>
                  </div>
                  
                  {session.country && (
                    <div className="session-detail">
                      <span className="detail-label">Country:</span>
                      <span className="detail-value">{session.country}</span>
                    </div>
                  )}
                  
                  {session.proxy && (
                    <div className="session-detail">
                      <span className="detail-label">Proxy:</span>
                      <span className="detail-value proxy" title={session.proxy}>
                        {session.proxy.length > 25 ? session.proxy.substring(0, 25) + '...' : session.proxy}
                      </span>
                    </div>
                  )}
                  
                  {session.duration !== undefined && session.duration !== null && (
                    <div className="session-detail">
                      <span className="detail-label">Duration:</span>
                      <span className="detail-value">{session.duration.toFixed(1)}s</span>
                    </div>
                  )}
                </div>
                
                <div className="session-time">
                  {formatDistanceToNow(new Date(session.start_time), { addSuffix: true })}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination">
              <button 
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage <= 1}
                className="page-btn"
              >
                ← Prev
              </button>
              
              <span className="page-info">
                Page {currentPage} of {totalPages}
              </span>
              
              <button 
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage >= totalPages}
                className="page-btn"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
