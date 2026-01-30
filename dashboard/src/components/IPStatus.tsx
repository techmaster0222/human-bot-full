import type { Stats } from '../types'
import './IPStatus.css'

interface IPStatusProps {
  stats: Stats | null
}

export default function IPStatus({ stats }: IPStatusProps) {
  if (!stats) {
    return (
      <div className="ip-status">
        <h2 className="section-title">IP Status</h2>
        <div className="empty-state">
          <p>No data available</p>
        </div>
      </div>
    )
  }

  const { ip_health, proxy_stats } = stats

  return (
    <div className="ip-status">
      <h2 className="section-title">IP Status</h2>
      
      {/* Health Summary */}
      <div className="ip-health-summary">
        <div className="health-item healthy">
          <span className="health-icon">🟢</span>
          <div className="health-content">
            <span className="health-value">{ip_health.healthy}</span>
            <span className="health-label">Healthy</span>
          </div>
        </div>
        <div className="health-item flagged">
          <span className="health-icon">🟡</span>
          <div className="health-content">
            <span className="health-value">{ip_health.flagged}</span>
            <span className="health-label">Flagged</span>
          </div>
        </div>
        <div className="health-item blacklisted">
          <span className="health-icon">🔴</span>
          <div className="health-content">
            <span className="health-value">{ip_health.blacklisted}</span>
            <span className="health-label">Blacklisted</span>
          </div>
        </div>
      </div>

      {/* Proxy List */}
      {proxy_stats.length === 0 ? (
        <div className="empty-state">
          <p>No proxies configured</p>
          <p className="hint">Proxy stats will appear when sessions use proxies</p>
        </div>
      ) : (
        <div className="proxy-list">
          {proxy_stats.map((proxy, index) => (
            <div key={proxy.url || index} className={`proxy-item ${proxy.status}`}>
              <div className="proxy-header">
                <span className="proxy-url" title={proxy.url}>
                  {proxy.url.length > 30 ? proxy.url.substring(0, 30) + '...' : proxy.url}
                </span>
                <span className={`proxy-status ${proxy.enabled ? 'active' : 'inactive'}`}>
                  {proxy.enabled ? '●' : '○'}
                </span>
              </div>
              <div className="proxy-metrics">
                <div className="metric">
                  <span className="metric-label">Uses:</span>
                  <span className="metric-value">{proxy.uses}</span>
                </div>
                <div className="metric">
                  <span className="metric-label">Success:</span>
                  <span className="metric-value">
                    {(proxy.success_rate * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="metric">
                  <span className={`metric-status ${proxy.status}`}>
                    {proxy.status}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
