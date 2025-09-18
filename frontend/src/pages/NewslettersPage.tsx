import React, { useEffect, useMemo, useState } from 'react'
import {
  createNewsletter,
  deleteNewsletter,
  getNewsletter,
  getRunDigest,
  listNewsletters,
  listRuns,
  NewsletterDetail,
  NewsletterFormValues,
  NewsletterSummary,
  resetNewsletter,
  RunSummary,
  triggerNewsletterRun,
  updateNewsletter,
  MetaOptions,
} from '../lib/api'
import { NewsletterForm } from '../components/NewsletterForm'

const formatDateTime = (value?: string | null) => {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch (error) {
    return value
  }
}

type DialogMode = 'create' | 'edit'

interface NewslettersPageProps {
  meta: MetaOptions | null
}

export const NewslettersPage: React.FC<NewslettersPageProps> = ({ meta }) => {
  const [newsletters, setNewsletters] = useState<NewsletterSummary[]>([])
  const [runMap, setRunMap] = useState<Record<number, RunSummary>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogMode, setDialogMode] = useState<DialogMode>('create')
  const [selected, setSelected] = useState<NewsletterDetail | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [runningId, setRunningId] = useState<number | null>(null)
  const [resettingId, setResettingId] = useState<number | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [digestHtml, setDigestHtml] = useState<string | null>(null)
  const [digestSubject, setDigestSubject] = useState<string>('')

  const loadNewsletters = async () => {
    setLoading(true)
    try {
      const data = await listNewsletters()
      setNewsletters(data)
      setError(null)
    } catch (err) {
      console.error(err)
      setError(err instanceof Error ? err.message : 'Failed to load newsletters.')
    } finally {
      setLoading(false)
    }
  }

  const loadRuns = async () => {
    try {
      const runs = await listRuns(100)
      const map: Record<number, RunSummary> = {}
      for (const run of runs) {
        if (!map[run.newsletter_id]) {
          map[run.newsletter_id] = run
        }
      }
      setRunMap(map)
    } catch (error) {
      console.error('Failed to load runs', error)
    }
  }

  useEffect(() => {
    loadNewsletters()
    loadRuns()
  }, [])

  useEffect(() => {
    if (!toast) return
    const id = window.setTimeout(() => setToast(null), 4000)
    return () => window.clearTimeout(id)
  }, [toast])

  const openCreateDialog = () => {
    setDialogMode('create')
    setSelected(null)
    setDialogOpen(true)
  }

  const openEditDialog = async (id: number) => {
    try {
      const detail = await getNewsletter(id)
      setSelected(detail)
      setDialogMode('edit')
      setDialogOpen(true)
    } catch (err) {
      setToast(err instanceof Error ? err.message : 'Failed to load newsletter details.')
    }
  }

  const handleCreate = async (values: NewsletterFormValues) => {
    setSubmitting(true)
    try {
      await createNewsletter(values)
      await loadNewsletters()
      await loadRuns()
      setDialogOpen(false)
      setToast('Newsletter created successfully.')
    } catch (err) {
      throw err
    } finally {
      setSubmitting(false)
    }
  }

  const handleUpdate = async (values: NewsletterFormValues) => {
    if (!selected) return
    setSubmitting(true)
    try {
      await updateNewsletter(selected.id, {
        name: values.name,
        timezone: values.timezone,
        schedule_times: values.schedule_times,
        include_watchlist: values.include_watchlist,
        custom_prompt: values.custom_prompt,
        feeds: values.feeds,
        watchlist_symbols: values.watchlist_symbols,
        active: values.active,
      })
      await loadNewsletters()
      await loadRuns()
      setDialogOpen(false)
      setToast('Newsletter updated.')
    } catch (err) {
      throw err
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this newsletter? This action cannot be undone.')) return
    try {
      await deleteNewsletter(id)
      await loadNewsletters()
      await loadRuns()
      setToast('Newsletter deleted.')
    } catch (err) {
      setToast(err instanceof Error ? err.message : 'Failed to delete newsletter.')
    }
  }

  const handleRun = async (newsletter: NewsletterSummary) => {
    setRunningId(newsletter.id)
    try {
      const result = await triggerNewsletterRun(newsletter.id)
      setToast(
        result.success
          ? `Run completed for ${newsletter.name}`
          : `Run for ${newsletter.name} reported an issue. Check logs.`,
      )
      await loadRuns()
    } catch (err) {
      setToast(err instanceof Error ? err.message : 'Failed to trigger run.')
    } finally {
      setRunningId(null)
    }
  }

  const handleReset = async (id: number) => {
    if (!confirm('Reset run history from the last 24 hours for this newsletter?')) {
      return
    }
    setResettingId(id)
    try {
      const response = await resetNewsletter(id, 24)
      setToast(`Reset completed. Deleted ${response.deleted_runs} runs.`)
      await loadRuns()
    } catch (err) {
      setToast(err instanceof Error ? err.message : 'Failed to reset runs.')
    } finally {
      setResettingId(null)
    }
  }

  const openDigest = async (newsletter: NewsletterSummary) => {
    const lastRun = runMap[newsletter.id]
    if (!lastRun) {
      setToast('No runs available for this newsletter yet.')
      return
    }
    try {
      const digest = await getRunDigest(lastRun.id)
      setDigestHtml(digest.html)
      setDigestSubject(digest.subject)
    } catch (err) {
      setToast(err instanceof Error ? err.message : 'Failed to fetch digest.')
    }
  }

  const closeDigest = () => {
    setDigestHtml(null)
    setDigestSubject('')
  }

  const latestRuns = useMemo(() => runMap, [runMap])

  return (
    <div className="page newsletters">
      <div className="dialog-header" style={{ marginBottom: 18 }}>
        <div>
          <h3 className="section-title">Newsletters</h3>
          <p className="muted">Configure schedules, feeds, watchlists, and prompts for each digest.</p>
        </div>
        <button className="btn primary" onClick={openCreateDialog}>
          New Newsletter
        </button>
      </div>

      {error && <div className="alert">{error}</div>}
      {toast && <div className="toast">{toast}</div>}

      {loading ? (
        <div className="spinner" aria-busy />
      ) : newsletters.length === 0 ? (
        <div className="empty-state">No newsletters yet. Create your first to get started.</div>
      ) : (
        <div className="newsletter-list">
          {newsletters.map((newsletter) => {
            const lastRun = latestRuns[newsletter.id]
            return (
              <div className="newsletter-item" key={newsletter.id}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <h4 style={{ margin: 0 }}>{newsletter.name}</h4>
                    <div className="muted">Slug: {newsletter.slug} · Timezone: {newsletter.timezone}</div>
                  </div>
                  <span className={`badge ${newsletter.active ? 'success' : 'danger'}`}>
                    {newsletter.active ? 'Active' : 'Paused'}
                  </span>
                </div>

                <div className="muted">Schedule: {newsletter.schedule_times.length ? newsletter.schedule_times.join(', ') : 'Uses defaults'}</div>
                {newsletter.include_watchlist && (
                  <div className="muted">Watchlist enabled</div>
                )}

                {lastRun && (
                  <div className="muted">
                    Last run {formatDateTime(lastRun.started_at)} · Status: {lastRun.status}
                  </div>
                )}

                <div className="button-row">
                  <button
                    className="btn success"
                    onClick={() => handleRun(newsletter)}
                    disabled={runningId === newsletter.id}
                  >
                    {runningId === newsletter.id ? 'Running…' : 'Run Now'}
                  </button>
                  <button
                    className="btn"
                    onClick={() => handleReset(newsletter.id)}
                    disabled={resettingId === newsletter.id}
                  >
                    {resettingId === newsletter.id ? 'Resetting…' : 'Reset 24h'}
                  </button>
                  <button className="btn" onClick={() => openEditDialog(newsletter.id)}>
                    Edit
                  </button>
                  <button className="btn" onClick={() => openDigest(newsletter)}>
                    View Last Digest
                  </button>
                  <button className="btn danger" onClick={() => handleDelete(newsletter.id)}>
                    Delete
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {dialogOpen && (
        <div className="dialog-backdrop" role="dialog" aria-modal>
          <div className="dialog">
            <div className="dialog-header">
              <h3 className="dialog-title">
                {dialogMode === 'create' ? 'Create Newsletter' : `Edit ${selected?.name}`}
              </h3>
              <button className="btn" onClick={() => setDialogOpen(false)}>
                Close
              </button>
            </div>
            <NewsletterForm
              initial={dialogMode === 'edit' ? selected : null}
              onSubmit={dialogMode === 'create' ? handleCreate : handleUpdate}
              onCancel={() => setDialogOpen(false)}
              submitting={submitting}
              timezoneOptions={meta?.timezones ?? []}
              defaultTimezone={meta?.default_timezone ?? 'UTC'}
            />
          </div>
        </div>
      )}

      {digestHtml && (
        <div className="dialog-backdrop" role="dialog" aria-modal>
          <div className="dialog" style={{ maxWidth: '960px' }}>
            <div className="dialog-header">
              <h3 className="dialog-title">{digestSubject}</h3>
              <button className="btn" onClick={closeDigest}>
                Close
              </button>
            </div>
            <div className="card" style={{ maxHeight: '70vh', overflow: 'auto' }}>
              <div dangerouslySetInnerHTML={{ __html: digestHtml }} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
