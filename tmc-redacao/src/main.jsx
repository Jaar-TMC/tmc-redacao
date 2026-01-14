import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Support both standalone (root) and WordPress (tmc-redacao-root) element IDs
const rootElement =
  document.getElementById('tmc-redacao-root') ||
  document.getElementById('root')

if (rootElement) {
  // Remove loading state if present (WordPress)
  const loadingEl = rootElement.querySelector('.tmc-loading')
  if (loadingEl) {
    loadingEl.remove()
  }

  createRoot(rootElement).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
} else {
  console.error('TMC Redacao: Root element not found')
}
