import type { BotEvent } from '../types'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts'
import './ActivityChart.css'

interface ActivityChartProps {
  events: BotEvent[]
}

interface ChartDataPoint {
  time: string
  sessions: number
  navigations: number
  errors: number
}

export default function ActivityChart({ events }: ActivityChartProps) {
  const chartData = processEventsForChart(events)

  return (
    <div className="activity-chart">
      <h2 className="section-title">Activity Timeline</h2>
      
      {chartData.length === 0 ? (
        <div className="empty-state">
          <p>No activity data yet</p>
          <p className="hint">Events will be plotted here as sessions run</p>
        </div>
      ) : (
        <div className="chart-container">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
              <XAxis
                dataKey="time"
                stroke="#94a3b8"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickMargin={8}
              />
              <YAxis
                stroke="#94a3b8"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                allowDecimals={false}
                width={30}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.95)',
                  border: '1px solid rgba(148, 163, 184, 0.3)',
                  borderRadius: '8px',
                  color: '#f1f5f9',
                  boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
                  fontSize: '12px'
                }}
              />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Line
                type="monotone"
                dataKey="sessions"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ fill: '#3b82f6', r: 3 }}
                name="Sessions"
              />
              <Line
                type="monotone"
                dataKey="navigations"
                stroke="#10b981"
                strokeWidth={2}
                dot={{ fill: '#10b981', r: 3 }}
                name="Navigations"
              />
              <Line
                type="monotone"
                dataKey="errors"
                stroke="#ef4444"
                strokeWidth={2}
                dot={{ fill: '#ef4444', r: 3 }}
                name="Errors"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

function processEventsForChart(events: BotEvent[]): ChartDataPoint[] {
  const timeMap = new Map<string, { sessions: number; navigations: number; errors: number }>()

  events.forEach((event) => {
    const date = new Date(event.timestamp)
    const minute = `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
    
    if (!timeMap.has(minute)) {
      timeMap.set(minute, { sessions: 0, navigations: 0, errors: 0 })
    }

    const data = timeMap.get(minute)!
    
    if (event.type === 'session_start' || event.type === 'session_end') {
      data.sessions++
    } else if (event.type === 'navigation' || event.type === 'click') {
      data.navigations++
    } else if (event.type === 'error') {
      data.errors++
    }
  })

  return Array.from(timeMap.entries())
    .map(([time, data]) => ({ time, ...data }))
    .sort((a, b) => a.time.localeCompare(b.time))
    .slice(-20) // Keep last 20 time points
}
