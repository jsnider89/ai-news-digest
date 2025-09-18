export const API_BASE = ((import.meta as any).env?.VITE_API_BASE || (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000')).replace(/\/$/, '')

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
    ...init,
  })

  if (response.status === 204) {
    return undefined as T
  }

  const contentType = response.headers.get('content-type') || ''
  const parseBody = async () => (contentType.includes('application/json') ? response.json() : response.text())

  if (!response.ok) {
    const body = await parseBody()
    const message = typeof body === 'string' ? body : JSON.stringify(body)
    throw new Error(`API ${response.status}: ${message}`)
  }

  return parseBody() as Promise<T>
}

export interface NewsletterFeedInput {
  url: string
  title?: string
  category?: string
  enabled?: boolean
}

export interface NewsletterFeed extends NewsletterFeedInput {
  enabled: boolean
}

export interface NewsletterSummary {
  id: number
  slug: string
  name: string
  timezone: string
  schedule_times: string[]
  include_watchlist: boolean
  newsletter_type: string
  verbosity_level: string
  custom_prompt: string
  active: boolean
}

export interface NewsletterDetail extends NewsletterSummary {
  feeds: NewsletterFeed[]
  watchlist_symbols: string[]
}

export interface NewsletterFormValues {
  slug: string
  name: string
  timezone: string
  schedule_times: string[]
  include_watchlist: boolean
  newsletter_type: string
  verbosity_level: string
  custom_prompt: string
  feeds: NewsletterFeedInput[]
  watchlist_symbols: string[]
  active: boolean
}

export interface RunSummary {
  id: number
  newsletter_id: number
  newsletter_name: string
  status: string
  started_at: string | null
  finished_at: string | null
  ai_provider?: string | null
  article_count: number
  error_message?: string | null
}

export interface RunResponse {
  newsletter_id: number
  success: boolean
  ai_provider: string
  articles: number
  feed_statuses: string[]
  subject?: string | null
  run_id?: number | null
}

export interface HealthMetrics {
  total_newsletters: number
  active_newsletters: number
  runs_today: number
  failed_runs_today: number
}

export interface SchedulerJob {
  id: string
  newsletter_id: number | null
  newsletter_name?: string | null
  next_run_time: string | null
  trigger: string
}

export interface NewsletterScheduleSummary {
  id: number
  name: string
  active: boolean
  schedule_times: string[]
  timezone: string
  next_run_times: string[]
}

export interface HealthResponse {
  status: string
  status_details: string[]
  timestamp: string
  metrics: HealthMetrics
  latest_run: RunSummary | null
  recent_runs: RunSummary[]
  newsletters: NewsletterScheduleSummary[]
  scheduler: {
    running: boolean
    job_count: number
    jobs: SchedulerJob[]
  }
}

export interface SettingsResponse {
  default_timezone: string
  default_send_times: string[]
  ai_provider_order: string[]
  primary_model: string
  secondary_model: string
  reasoning_level: string
  resend_from_email: string
  resend_from_name: string
  default_recipients: string[]
  available_models: string[]
  available_reasoning_levels: string[]
}

export interface SettingsUpdatePayload {
  default_timezone?: string
  default_send_times?: string[]
  primary_model?: string
  secondary_model?: string
  reasoning_level?: string
  default_recipients?: string[]
}

export interface MetaOptions {
  timezones: Array<{ value: string; label: string }>
  models: Array<{ value: string; label: string; provider: string; supports_reasoning: boolean }>
  reasoning_levels: string[]
  default_timezone: string
}

export interface LogEntry {
  timestamp: string
  level: string
  logger: string
  message: string
  exception?: string
}

export interface LogResponse {
  entries: LogEntry[]
  count: number
  available: number
  capacity: number
  limit: number
  run_id?: number
}

export function listNewsletters(): Promise<NewsletterSummary[]> {
  return api('/api/newsletters')
}

export function getNewsletter(id: number): Promise<NewsletterDetail> {
  return api(`/api/newsletters/${id}`)
}

export function createNewsletter(payload: NewsletterFormValues): Promise<NewsletterDetail> {
  const { active, ...body } = payload
  return api('/api/newsletters', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateNewsletter(id: number, payload: Partial<NewsletterFormValues>): Promise<NewsletterDetail> {
  const { slug, ...rest } = payload
  return api(`/api/newsletters/${id}`, {
    method: 'PUT',
    body: JSON.stringify(rest),
  })
}

export function deleteNewsletter(id: number): Promise<void> {
  return api(`/api/newsletters/${id}`, { method: 'DELETE' })
}

export function triggerNewsletterRun(id: number): Promise<RunResponse> {
  return api(`/api/newsletters/${id}/run`, { method: 'POST' })
}

export function resetNewsletter(id: number, hours: number): Promise<{ deleted_runs: number }> {
  return api(`/api/newsletters/${id}/reset?hours=${hours}`, { method: 'POST' })
}

export function getHealth(): Promise<HealthResponse> {
  return api('/health')
}

export function listRuns(limit = 50): Promise<RunSummary[]> {
  return api(`/api/runs?limit=${limit}`)
}

export function getRunDigest(runId: number): Promise<{ run_id: number; subject: string; html: string }>
export function getRunDigest(runId: string): Promise<{ run_id: number; subject: string; html: string }>
export function getRunDigest(runId: number | string) {
  return api(`/api/runs/${runId}/digest`)
}

export function getSettings(): Promise<SettingsResponse> {
  return api('/api/settings')
}

export function updateSettings(payload: SettingsUpdatePayload): Promise<SettingsResponse> {
  return api('/api/settings', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function getMetaOptions(): Promise<MetaOptions> {
  return api('/api/meta/options')
}

export function getLogs(limit = 200, runId?: number): Promise<LogResponse> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (typeof runId === 'number') {
    params.set('run_id', String(runId))
  }
  return api(`/api/logs?${params.toString()}`)
}

export function clearLogs(): Promise<{ cleared: boolean }> {
  return api('/api/logs', { method: 'DELETE' })
}
