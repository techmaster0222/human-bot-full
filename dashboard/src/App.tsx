import { useEffect } from 'react'
import { ThemeProvider } from './context/ThemeContext'
import Dashboard from './components/Dashboard'
import { wsService } from './services/websocket'
import './App.css'

function App() {
  useEffect(() => {
    // Connect WebSocket after a short delay
    const connectTimeout = setTimeout(() => {
      wsService.connect()
    }, 500)

    // Keep-alive ping every 30 seconds
    const pingInterval = setInterval(() => {
      wsService.ping()
    }, 30000)

    return () => {
      clearTimeout(connectTimeout)
      clearInterval(pingInterval)
      wsService.disconnect()
    }
  }, [])

  return (
    <ThemeProvider>
      <div className="app">
        <header className="app-header">
          <h1>Human Bot Dashboard</h1>
          <p>Real-time Bot Engine Monitoring</p>
        </header>
        <Dashboard />
      </div>
    </ThemeProvider>
  )
}

export default App
