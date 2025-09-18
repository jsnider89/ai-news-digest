import React, { useEffect, useMemo, useState } from 'react'
import { getHealth, HealthResponse } from '../lib/api'

const REFRESH_MS = 30_000

const formatDateTime = (value?: string | null) => {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch (error) {
    return value
  }
}

const statusLabel: Record<string, { label: string; className: string }> = {
  ok: { label: 'Operational', className: 'status-pill ok' },
  degraded: { label: 'Degraded', className: 'status-pill degraded' },
  issues: { label: 'Attention Needed', className: 'status-pill issues' },
}

export const DashboardPage: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    try {
      setLoading(true)
      const data = await getHealth()
      setHealth(data)
      setError(null)
    } catch (err) {
      console.error(err)
      setError(err instanceof Error ? err.message : 'Failed to load health data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const interval = window.setInterval(load, REFRESH_MS)
    return () => window.clearInterval(interval)
  }, [])

  const statusMeta = statusLabel[health?.status ?? 'ok'] ?? statusLabel.ok

  const recentRuns = useMemo(() => health?.recent_runs?.slice(0, 5) ?? [], [health])
  const upcoming = useMemo(() => health?.newsletters ?? [], [health])

  if (loading && !health) {
    return (
      <div className="spinner" aria-busy />
    )
  }

  if (error && !health) {
    return <div className="alert">{error}</div>
  }

  return (
    <div className="page dashboard">
      <div className="hero">
        <div className="tagline">Market Aggregator Control Center</div>
        <h2>Operational Overview</h2>
        <p>Monitor newsletter health, pipeline performance, and upcoming schedules at a glance.</p>
        <div className={statusMeta.className}>
          {statusMeta.label}
          {health?.status_details && health.status_details.length > 0 && (
            <div className="status-details">
              {health.status_details.map((detail, i) => (
                <div key={i} className="status-detail">{detail}</div>
              ))}
            </div>
          )}
        </div>
      </div>

      {error && <div className="alert">{error}</div>}

      <div className="card-grid three">
        <div className="card">
          <div className="metric-value">{health?.metrics.total_newsletters ?? 0}</div>
          <div className="metric-label">Configured Newsletters</div>
        </div>
        <div className="card">
          <div className="metric-value">{health?.metrics.active_newsletters ?? 0}</div>
          <div className="metric-label">Active Schedules</div>
        </div>
        <div className="card">
          <div className="metric-value">{health?.metrics.runs_today ?? 0}</div>
          <div className="metric-label">Runs Triggered Today</div>
        </div>
      </div>

      <div className="card-grid two" style={{ marginTop: 24 }}>
        <div className="card">
          <h3>Latest Run</h3>
          {health?.latest_run ? (
            <>
              <p className="muted">{health.latest_run.newsletter_name}</p>
              <div className="inline-list" style={{ marginBottom: 12 }}>
                <span className={`badge ${health.latest_run.status === 'success' ? 'success' : 'danger'}`}>
                  {health.latest_run.status.toUpperCase()}
                </span>
                {health.latest_run.ai_provider && <span className="badge info">{health.latest_run.ai_provider}</span>}
              </div>
              <p>
                <strong>Started:</strong> {formatDateTime(health.latest_run.started_at)}
              </p>
              <p>
                <strong>Finished:</strong> {formatDateTime(health.latest_run.finished_at)}
              </p>
              <p>
                <strong>Articles:</strong> {health.latest_run.article_count}
              </p>
              {health.latest_run.error_message && (
                <p className="muted">Error: {health.latest_run.error_message}</p>
              )}
            </>
          ) : (
            <p className="muted">No runs recorded yet.</p>
          )}
        </div>

        <div className="card">
          <h3>Upcoming Schedule</h3>
          {upcoming.length === 0 ? (
            <p className="muted">No newsletters configured.</p>
          ) : (
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr>
                    <th>Newsletter</th>
                    <th>Next Runs</th>
                  </tr>
                </thead>
                <tbody>
                  {upcoming.slice(0, 5).map((newsletter) => (
                    <tr key={newsletter.id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{newsletter.name}</div>
                        <div className="muted small">{newsletter.timezone}</div>
                      </td>
                      <td>
                        {newsletter.next_run_times && newsletter.next_run_times.length > 0 ? (
                          <div className="inline-list">
                            {newsletter.next_run_times.slice(0, 3).map((run) => (
                              <span key={run} className="badge info">
                                {formatDateTime(run)}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="muted">Awaiting schedule refresh…</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 24 }}>
        <div className="dialog-header">
          <h3 className="section-title">Recent Runs</h3>
          <button className="btn" onClick={load} disabled={loading}>
            Refresh
          </button>
        </div>
        {recentRuns.length === 0 ? (
          <div className="empty-state">No run history available yet.</div>
        ) : (
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Newsletter</th>
                  <th>Status</th>
                  <th>Started</th>
                  <th>Finished</th>
                  <th>Provider</th>
                  <th>Articles</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run) => (
                  <tr key={run.id}>
                    <td>{run.newsletter_name}</td>
                    <td>
                      <span className={`badge ${run.status === 'success' ? 'success' : 'danger'}`}>
                        {run.status.toUpperCase()}
                      </span>
                    </td>
                    <td>{formatDateTime(run.started_at)}</td>
                    <td>{formatDateTime(run.finished_at)}</td>
                    <td>{run.ai_provider || '—'}</td>
                    <td>{run.article_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
