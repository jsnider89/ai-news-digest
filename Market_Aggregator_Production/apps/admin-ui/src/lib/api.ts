const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'https://ai-market-intel-worker.jonsnider.workers.dev'

async function api(path: string, init: RequestInit = {}) {
  const r = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init.headers || {}) },
    ...init,
  })
  const ct = r.headers.get('content-type') || ''
  if (!r.ok) {
    const msg = ct.includes('application/json') ? JSON.stringify(await r.json()) : await r.text()
    throw new Error(`API ${r.status}: ${msg}`)
  }
  return ct.includes('application/json') ? r.json() : r.text()
}

export async function getHealth() { return api('/health') }

export async function getFeeds() { return api('/admin/api/feeds') }

export async function getSettings() { return api('/admin/api/settings') }

export async function updateSettings(settings: Record<string, any>) { return api('/admin/api/settings', { method: 'PUT', body: JSON.stringify(settings) }) }

export async function addFeed(feed: { name: string; url: string; category?: string; enabled?: number }) { return api('/admin/api/feeds', { method: 'POST', body: JSON.stringify(feed) }) }

export async function updateFeed(id: number, updates: Record<string, any>) { return api(`/admin/api/feeds/${id}`, { method: 'PUT', body: JSON.stringify(updates) }) }

export async function deleteFeed(id: number) { return api(`/admin/api/feeds/${id}`, { method: 'DELETE' }) }

export async function triggerRun() { return api('/cron', { method: 'POST' }) }

export async function resetSeen(hours: number) { return api('/admin/api/reset-seen', { method: 'POST', body: JSON.stringify({ hours }) }) }

export async function getRuns(limit = 50) { return api(`/admin/api/runs?limit=${limit}`) }

export function getRunDigestUrl(runId: string) {
  return `${API_BASE}/admin/api/runs/${runId}/digest`
}

export async function getRunLogs(runId: string) { return api(`/admin/api/runs/${runId}/logs`) }

export async function getPrompt() { return api('/admin/api/prompt') }

export async function updatePrompt(prompt: string) { return api('/admin/api/prompt', { method: 'PUT', body: JSON.stringify({ prompt }) }) }

export { API_BASE }
