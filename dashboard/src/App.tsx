import { useState, useEffect } from 'react'
import { ThemeProvider } from './context/ThemeContext'
import Dashboard from './components/Dashboard'
import './App.css'

function App() {
  return (
    <ThemeProvider>
      <Dashboard />
    </ThemeProvider>
  )
}

export default App
