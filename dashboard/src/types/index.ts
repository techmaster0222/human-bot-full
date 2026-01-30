/**
 * TypeScript Types for Dashboard
 */

export interface Session {
  session_id: string
  profile_id: string
  device: string
  start_time: string
  target_url?: string
  proxy?: string
  country?: string
  status: 'active' | 'completed' | 'failed'
  duration?: number
  success?: boolean
}

export interface PaginatedSessions {
  sessions: Session[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface Stats {
  total_sessions: number
  active_sessions: number
  successful_sessions: number
  failed_sessions: number
  total_events: number
  average_duration: number
  success_rate: number
  proxy_stats: ProxyStat[]
  ip_health: {
    healthy: number
    flagged: number
    blacklisted: number
  }
}

export interface ProxyStat {
  url: string
  uses: number
  successes: number
  failures: number
  success_rate: number
  status: 'healthy' | 'flagged' | 'blacklisted'
  enabled: boolean
  last_used?: string
  avg_latency_ms?: number
  country?: string
}

export interface BotEvent {
  id?: number
  type: string
  timestamp: string
  session_id?: string
  data: Record<string, any>
}

export interface PaginatedEvents {
  events: BotEvent[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface HealthCheck {
  status: string
  timestamp: string
  active_sessions: number
  database_path: string
  version: string
  auth_enabled: boolean
  rate_limiting: boolean
}

export interface SessionFilters {
  status?: 'active' | 'completed' | 'failed' | ''
  country?: string
  search?: string
  page: number
  per_page: number
}

export type Theme = 'dark' | 'light'
