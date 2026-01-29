export interface Session {
  id: string
  profile_id: string
  device: string
  target_url: string
  proxy: string
  country: string
  status: 'active' | 'completed' | 'failed'
  start_time: string
  end_time?: string
  duration?: number
  success?: boolean
}

export interface Event {
  id: number
  session_id: string
  event_type: string
  timestamp: string
  data: Record<string, unknown>
}

export interface Stats {
  total_sessions: number
  active_sessions: number
  successful_sessions: number
  failed_sessions: number
  success_rate: number
  proxy_stats: ProxyStats[]
  ip_health: IPHealth
}

export interface ProxyStats {
  proxy_id: string
  success_rate: number
  avg_latency_ms: number
  status: 'healthy' | 'flagged' | 'blacklisted'
}

export interface IPHealth {
  healthy: number
  flagged: number
  blacklisted: number
}
