import React, { useEffect, useMemo, useState } from 'react'
import { clearLogs, getHealth, getLogs, HealthResponse, LogEntry } from '../lib/api'

const LOG_REFRESH_MS = 10_000
const HEALTH_REFRESH_MS = 30_000

const formatDateTime = (value?: string | null) => {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch (error) {
    return value
  }
}

export const HealthPage: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [loadingHealth, setLoadingHealth] = useState(true)
  const [loadingLogs, setLoadingLogs] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [logError, setLogError] = useState<string | null>(null)
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null)

  const loadHealth = async () => {
    try {
      setLoadingHealth(true)
      const data = await getHealth()
      setHealth(data)
      setError(null)
    } catch (err) {
      console.error(err)
      setError(err instanceof Error ? err.message : 'Failed to load health metrics.')
    } finally {
      setLoadingHealth(false)
    }
  }

  const loadLogs = async (overrideRunId: number | null = selectedRunId) => {
    try {
      setLoadingLogs(true)
      const payload = await getLogs(250, overrideRunId === null ? undefined : overrideRunId)
      setLogs(payload.entries)
      setLogError(null)
    } catch (err) {
      console.error(err)
      setLogError(err instanceof Error ? err.message : 'Failed to load logs.')
    } finally {
      setLoadingLogs(false)
    }
  }

  useEffect(() => {
    loadHealth()
    const interval = window.setInterval(loadHealth, HEALTH_REFRESH_MS)
    return () => window.clearInterval(interval)
  }, [])

  useEffect(() => {
    loadLogs(selectedRunId)
    if (selectedRunId === null) {
      const interval = window.setInterval(() => loadLogs(null), LOG_REFRESH_MS)
      return () => window.clearInterval(interval)
    }
    return undefined
  }, [selectedRunId])

  const runOptions = useMemo(() => {
    if (!health) return []
    const seen = new Set<number>()
    const entries: HealthResponse['recent_runs'] = []
    if (health.latest_run && !seen.has(health.latest_run.id)) {
      entries.push(health.latest_run)
      seen.add(health.latest_run.id)
    }
    for (const run of health.recent_runs) {
      if (!seen.has(run.id)) {
        entries.push(run)
        seen.add(run.id)
      }
    }
    return entries
  }, [health])

  const selectedRun = useMemo(
    () => runOptions.find((run) => run.id === selectedRunId) ?? null,
    [runOptions, selectedRunId]
  )

  const handleSourceChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value
    setSelectedRunId(value ? Number(value) : null)
  }

  const handleClear = async () => {
    if (selectedRunId !== null) return
    await clearLogs()
    await loadLogs(null)
  }

  return (
    <div className="page health">
      <div className="card-grid two">
        <div className="card">
          <div className="dialog-header">
            <h3 className="section-title">System Snapshot</h3>
            <button className="btn" onClick={loadHealth} disabled={loadingHealth}>
              Refresh
            </button>
          </div>
          {error && <div className="alert">{error}</div>}
          {loadingHealth && !health ? (
            <div className="spinner" aria-busy />
          ) : (
            <>
              <p className="muted">Last updated {formatDateTime(health?.timestamp)}</p>
              <div className="card-grid two" style={{ marginTop: 16 }}>
                <div>
                  <div className="metric-value">{health?.metrics.runs_today ?? 0}</div>
                  <div className="metric-label">Runs Today</div>
                </div>
                <div>
                  <div className="metric-value">{health?.metrics.failed_runs_today ?? 0}</div>
                  <div className="metric-label">Failures Today</div>
                </div>
              </div>
              <hr className="divider" />
              <h4>Scheduler Jobs</h4>
              {health && health.scheduler.jobs.length > 0 ? (
                <div className="scheduler-list">
                  {health.scheduler.jobs.map((job) => (
                    <div className="scheduler-item" key={job.id}>
                      <div className="scheduler-name">
                        {job.newsletter_name || `Newsletter #${job.newsletter_id ?? '—'}`}
                      </div>
                      <div className="scheduler-next">Next run {formatDateTime(job.next_run_time)}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted">Scheduler is idle. Activate at least one newsletter to enqueue runs.</p>
              )}
            </>
          )}
        </div>

        <div className="card">
          <div className="dialog-header">
            <h3 className="section-title">Recent Logs</h3>
            <div className="button-row">
              <select className="select" value={selectedRunId ?? ''} onChange={handleSourceChange}>
                <option value="">Live Buffer</option>
                {runOptions.map((run) => (
                  <option value={run.id} key={run.id}>
                    #{run.id} · {run.newsletter_name || 'Newsletter'} · {formatDateTime(run.started_at)}
                  </option>
                ))}
              </select>
              <button className="btn" onClick={() => loadLogs(selectedRunId)} disabled={loadingLogs}>
                Refresh
              </button>
              <button className="btn danger" onClick={handleClear} disabled={selectedRunId !== null}>
                Clear Logs
              </button>
            </div>
          </div>
          {logError && <div className="alert">{logError}</div>}
          {selectedRunId !== null && (
            <p className="muted" style={{ marginBottom: 12 }}>
              Viewing archived logs for run #{selectedRunId}
              {selectedRun ? ` · ${selectedRun.newsletter_name} · ${formatDateTime(selectedRun.started_at)}` : ''}
            </p>
          )}
          {loadingLogs && logs.length === 0 ? (
            <div className="spinner" aria-busy />
          ) : logs.length === 0 ? (
            <div className="empty-state">No log entries captured yet.</div>
          ) : (
            <div className="log-view">
              {logs.map((entry) => (
                <div className="log-row" key={`${entry.timestamp}-${entry.message}`}>
                  <span className="log-timestamp">{formatDateTime(entry.timestamp)}</span>
                  <span className="log-level">[{entry.level}]</span>
                  <span className="log-message">{entry.message}</span>
                  {entry.exception && (
                    <pre className="code-frame" style={{ marginTop: 8 }}>{entry.exception}</pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
