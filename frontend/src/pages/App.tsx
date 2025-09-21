import React, { useEffect, useState } from 'react'
import { DashboardPage } from './DashboardPage'
import { NewslettersPage } from './NewslettersPage'
import { HealthPage } from './HealthPage'
import { SettingsPage } from './SettingsPage'
import { getMetaOptions, MetaOptions } from '../lib/api'

type View = 'dashboard' | 'newsletters' | 'health' | 'settings'

const NAV_ITEMS: Array<{ key: View; label: string }> = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'newsletters', label: 'Newsletters' },
  { key: 'health', label: 'Health & Logs' },
  { key: 'settings', label: 'Global Settings' },
]

export const App: React.FC = () => {
  const [view, setView] = useState<View>('dashboard')
  const [meta, setMeta] = useState<MetaOptions | null>(null)
  const [metaError, setMetaError] = useState<string | null>(null)
  const [navOpen, setNavOpen] = useState(false)


  useEffect(() => {
    getMetaOptions()
      .then((options) => {
        setMeta(options)
        setMetaError(null)
        // Update document title with app name
        document.title = options.app_name ? `${options.app_name} Admin` : 'Admin Panel'
      })
      .catch((error) => {
        console.error('Failed to load meta options', error)
        setMetaError('Failed to load configuration options. Some forms may be limited.')
      })
  }, [])

  useEffect(() => {
    const hash = window.location.hash.replace('#', '') as View
    if (hash && NAV_ITEMS.some((item) => item.key === hash)) {
      setView(hash)
    }
    const listener = () => {
      const next = window.location.hash.replace('#', '') as View
      if (next && NAV_ITEMS.some((item) => item.key === next)) {
        setView(next)
      }
    }
    window.addEventListener('hashchange', listener)
    return () => window.removeEventListener('hashchange', listener)
  }, [])

  useEffect(() => {
    window.location.hash = view
  }, [view])

  // Close mobile nav when window resizes to desktop
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 768) {
        setNavOpen(false)
      }
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="container">
          <div className="header-bar">
            <h1 className="app-title">{meta?.app_name ? `${meta.app_name} Admin` : 'Admin'}</h1>
            <button
              className="nav-toggle"
              type="button"
              aria-expanded={navOpen}
              aria-controls="primary-nav"
              onClick={() => setNavOpen(!navOpen)}
            >
              <span className="icon" aria-hidden="true"></span>
              Menu
            </button>
          </div>
          <nav className="nav" id="primary-nav" data-open={navOpen ? "true" : "false"} aria-label="Primary navigation">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.key}
                className={`nav-button ${item.key === view ? 'active' : ''}`}
                onClick={() => {
                  setView(item.key)
                  setNavOpen(false) // Close menu on mobile after selection
                }}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="app-main">
        <div className="container">
          {metaError && <div className="alert">{metaError}</div>}
          {view === 'dashboard' && <DashboardPage meta={meta} />}
          {view === 'newsletters' && <NewslettersPage meta={meta} />}
          {view === 'health' && <HealthPage />}
          {view === 'settings' && <SettingsPage meta={meta} />}
        </div>
      </main>
    </div>
  )
}
