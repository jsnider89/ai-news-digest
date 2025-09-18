import React, { useEffect, useState } from 'react'
import { getHealth, getSettings, getFeeds, updateSettings, addFeed, updateFeed, deleteFeed, triggerRun, getRuns, getRunLogs, getRunDigestUrl, getPrompt, updatePrompt, resetSeen, API_BASE } from '../lib/api'

type Tab = 'Dashboard' | 'Feeds' | 'Settings' | 'Runs' | 'Prompt'

export function App() {
  const [tab, setTab] = useState<Tab>('Dashboard')
  return (
    <div>
      <div className="header">
        <div className="container">
          <h2 className="title">AI Market Intel – Admin</h2>
          <div className="nav">
            {(['Dashboard','Feeds','Settings','Runs','Prompt'] as Tab[]).map(t => (
              <button key={t} onClick={() => setTab(t)} className={`tab-btn ${t===tab?'active':''}`}>{t}</button>
            ))}
          </div>
        </div>
      </div>
      <div className="container content">
        {tab === 'Dashboard' && <Dashboard/>}
        {tab === 'Feeds' && <Feeds/>}
        {tab === 'Settings' && <Settings/>}
        {tab === 'Runs' && <Runs/>}
        {tab === 'Prompt' && <PromptEditor/>}
      </div>
    </div>
  )
}

function Dashboard() {
  const [health, setHealth] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [runInProgress, setRunInProgress] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [resetResult, setResetResult] = useState<{ hours: number, before: number, deleted: number, after: number } | null>(null)
  
  useEffect(() => { 
    getHealth()
      .then(setHealth)
      .catch(err => {
        console.error('Health check failed:', err)
        setHealth({ error: 'Failed to load health data' })
      })
      .finally(() => setLoading(false))
  }, [])

  const handleManualRun = async () => {
    if (runInProgress) return
    
    setRunInProgress(true)
    try {
      const result = await triggerRun()
      
      if (result.status === 'success' || result.status === 'partial') {
        const message = `✅ Run completed successfully!
        
📊 Results:
• Status: ${result.status}
• Feeds processed: ${result.feeds_ok}/${result.feeds_total}
• New articles: ${result.new_articles}
• Articles used for AI: ${result.used}
• Email sent: ${result.email_ok ? 'Yes' : 'No'}
• Run ID: ${result.run_id}

${result.status === 'partial' ? '⚠️ Some feeds failed, but digest was generated successfully.' : ''}
        
🔗 View the latest digest to see results!`
        
        alert(message)
      } else {
        alert(`❌ Run failed: ${result.error || 'Unknown error'}`)
      }
      
      // Refresh health data
      getHealth().then(setHealth).catch(() => {})
      
    } catch (error) {
      alert('❌ Error triggering run: ' + String(error))
    } finally {
      setRunInProgress(false)
    }
  }

  const handleResetSeen = async (hours: number) => {
    if (resetting) return
    if (!confirm(`Reset 'seen' hashes for the last ${hours} hours? This will cause recent articles to be reprocessed on the next run.`)) return
    setResetting(true)
    try {
      const res = await resetSeen(hours)
      if (res?.ok) {
        setResetResult({ hours: res.hours, before: res.before ?? 0, deleted: res.deleted ?? 0, after: res.after ?? 0 })
        alert(`✅ Reset complete. Deleted ${res.deleted} of ${res.before} entries from the last ${res.hours} hours. Remaining: ${res.after}.`)
      } else {
        setResetResult(null)
        alert(`❌ Reset failed: ${res?.error || 'Unknown error'}`)
      }
    } catch (e) {
      alert('❌ Error resetting: ' + String(e))
    } finally {
      setResetting(false)
    }
  }

  if (loading) return <div className="card">Loading...</div>

  return (
    <div>
      <h3 style={{ margin: '4px 0 12px' }}>📊 System Dashboard</h3>
      <div className="grid grid-2" style={{ marginBottom: 16 }}>
        <div className="card">
          <h4>🟢 System Status</h4>
          <div className="muted">{health?.ok ? 'All systems operational' : 'System issues detected'}</div>
        </div>
        {health?.latest && (
          <div className="card">
            <h4>📈 Last Run</h4>
            <div><strong>Run ID:</strong> <span style={{ fontFamily: 'monospace' }}>{health.latest.run_id}</span></div>
            <div><strong>Status:</strong> {health.latest.status}</div>
            <div><strong>Started:</strong> {new Date(health.latest.started_at).toLocaleString()}</div>
            {health.latest.finished_at && (<div><strong>Finished:</strong> {new Date(health.latest.finished_at).toLocaleString()}</div>)}
          </div>
        )}
      </div>

      <div className="grid grid-2" style={{ marginBottom: 16 }}>
        <div className="card">
          <h4>🧹 Reset Recent Articles</h4>
          <p className="muted">Clear dedupe memory for recent items so a manual run can reprocess them.</p>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => handleResetSeen(12)} disabled={resetting} className="btn danger">{resetting ? 'Resetting…' : 'Reset last 12h'}</button>
            <button onClick={() => handleResetSeen(24)} disabled={resetting} className="btn">{resetting ? 'Resetting…' : 'Reset last 24h'}</button>
          </div>
          {resetResult && (
            <div style={{ marginTop: 8, fontSize: 13, color: '#444' }}>
              <div><strong>Last reset:</strong> {resetResult.hours}h window</div>
              <div>Deleted {resetResult.deleted} of {resetResult.before}; remaining in window: {resetResult.after}</div>
            </div>
          )}
        </div>
        <div className="card">
          <h4>⚙️ Actions</h4>
          <div style={{ display: 'flex', gap: 8 }}>
            <a href={`${API_BASE}/latest`} target="_blank" rel="noreferrer" className="button-link"><button className="btn primary">📰 View Latest Digest</button></a>
            <button onClick={handleManualRun} disabled={runInProgress} className="btn success">{runInProgress ? '⏳ Running…' : '🔄 Trigger Manual Run'}</button>
          </div>
        </div>
      </div>

      {health?.error && (
        <div className="card" style={{ borderColor: '#f5c6cb', background: '#f8d7da', color: '#721c24' }}>
          <strong>Error:</strong> {health.error}
        </div>
      )}
    </div>
  )
}

function Feeds() {
  const [feeds, setFeeds] = useState<any[]>([])
  const [showAddForm, setShowAddForm] = useState(false)
  const [newFeed, setNewFeed] = useState({ name: '', url: '', category: '', enabled: 1 })
  
  const loadFeeds = () => getFeeds().then((r:any)=>setFeeds(r.feeds||[])).catch(()=>{})
  useEffect(() => { loadFeeds() }, [])

  const handleAddFeed = async () => {
    try {
      const result = await addFeed(newFeed)
      setNewFeed({ name: '', url: '', category: '', enabled: 1 })
      setShowAddForm(false)
      loadFeeds()
      alert('Feed added successfully!')
    } catch (e) {
      alert('Error adding feed: ' + String(e))
    }
  }

  const handleToggleEnabled = async (feed: any) => {
    try {
      await updateFeed(feed.id, { enabled: feed.enabled ? 0 : 1 })
      loadFeeds()
    } catch (e) {
      alert('Error updating feed')
    }
  }

  const handleDeleteFeed = async (id: number) => {
    if (confirm('Delete this feed?')) {
      try {
        await deleteFeed(id)
        loadFeeds()
      } catch (e) {
        alert('Error deleting feed')
      }
    }
  }

  return (
    <div>
      <div className="card" style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>RSS Feeds</h3>
        <button onClick={() => setShowAddForm(!showAddForm)} className="btn primary">{showAddForm ? 'Cancel' : 'Add Feed'}</button>
      </div>

      {showAddForm && (
        <div className="card" style={{ marginBottom: 12 }}>
          <h4>Add New Feed</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 1fr auto', gap: 8, alignItems: 'center' }}>
            <input placeholder="Name" value={newFeed.name} onChange={e => setNewFeed({...newFeed, name: e.target.value})} className="input" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 4 }} />
            <input placeholder="URL" value={newFeed.url} onChange={e => setNewFeed({...newFeed, url: e.target.value})} className="input" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 4 }} />
            <input placeholder="Category" value={newFeed.category} onChange={e => setNewFeed({...newFeed, category: e.target.value})} className="input" style={{ padding: 8, border: '1px solid #ddd', borderRadius: 4 }} />
            <button onClick={handleAddFeed} className="btn success">Add</button>
          </div>
        </div>
      )}

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>URL</th>
              <th>Category</th>
              <th style={{ textAlign: 'center' }}>Status</th>
              <th style={{ textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {feeds.map(f => (
              <tr key={f.id}>
                <td>{f.name}</td>
                <td>
                  <a href={f.url} target="_blank" rel="noreferrer" style={{ color: '#0b79d0', textDecoration: 'none' }}>
                    {f.url.length > 50 ? f.url.substring(0, 50) + '...' : f.url}
                  </a>
                </td>
                <td>{f.category || '-'}</td>
                <td style={{ textAlign: 'center' }}>
                  <button onClick={() => handleToggleEnabled(f)} className={`btn ${f.enabled ? 'success' : 'danger'}`}>
                    {f.enabled ? 'Enabled' : 'Disabled'}
                  </button>
                </td>
                <td style={{ textAlign: 'center' }}>
                  <button onClick={() => handleDeleteFeed(f.id)} className="btn danger">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Settings() {
  const [settings, setSettings] = useState<any>({})
  const [editMode, setEditMode] = useState(false)
  const [formData, setFormData] = useState<any>({
    emails: [''],
    times: ['06:30', '17:30'],
    symbols: ['SPY', 'QQQ', 'IWM'],
    max_concurrency: '6',
    max_articles_considered: '60',
    max_articles_for_ai: '25',
    email_from: '',
    per_source_cap: '10',
    ai_primary: 'gemini',
    gemini_model_id: 'gemini-2.5-flash',
    openai_model_id: 'gpt-5-mini',
    openai_reasoning: 'medium'
  })

  const loadSettings = () => getSettings().then((r:any)=>setSettings(r.settings||{})).catch(()=>{})
  useEffect(() => { loadSettings() }, [])

  const parseJsonArray = (str: string): string[] => {
    try {
      return JSON.parse(str || '[]')
    } catch {
      return []
    }
  }

  const startEdit = () => {
    setFormData({
      emails: parseJsonArray(settings.recipient_emails).length > 0 ? parseJsonArray(settings.recipient_emails) : [''],
      times: parseJsonArray(settings.digest_times).length > 0 ? parseJsonArray(settings.digest_times) : ['06:30', '17:30'],
      symbols: parseJsonArray(settings.watchlist).length > 0 ? parseJsonArray(settings.watchlist) : ['SPY', 'QQQ', 'IWM'],
      max_concurrency: settings.max_concurrency || '6',
      max_articles_considered: settings.max_articles_considered || '60',
      max_articles_for_ai: settings.max_articles_for_ai || '25',
      email_from: settings.email_from || '',
      per_source_cap: settings.per_source_cap || '10',
      ai_primary: settings.ai_primary || 'gemini',
      gemini_model_id: settings.gemini_model_id || 'gemini-2.5-flash',
      openai_model_id: settings.openai_model_id || 'gpt-5-mini',
      openai_reasoning: settings.openai_reasoning || 'medium'
    })
    setEditMode(true)
  }

  const handleSave = async () => {
    try {
      const payload = {
        recipient_emails: JSON.stringify(formData.emails.filter(e => e.trim())),
        digest_times: JSON.stringify(formData.times.filter(t => t.trim())),
        watchlist: JSON.stringify(formData.symbols.filter(s => s.trim())),
        max_concurrency: formData.max_concurrency,
        max_articles_considered: formData.max_articles_considered,
        max_articles_for_ai: formData.max_articles_for_ai,
        email_from: formData.email_from,
        per_source_cap: String(formData.per_source_cap || '10'),
        ai_primary: formData.ai_primary,
        gemini_model_id: formData.gemini_model_id,
        openai_model_id: formData.openai_model_id,
        openai_reasoning: formData.openai_reasoning
      }
      await updateSettings(payload)
      setEditMode(false)
      loadSettings()
      alert('Settings updated successfully!')
    } catch (e) {
      alert('Error updating settings')
    }
  }

  const addField = (field: 'emails' | 'times' | 'symbols') => {
    setFormData({...formData, [field]: [...formData[field], '']})
  }

  const removeField = (field: 'emails' | 'times' | 'symbols', index: number) => {
    const newArray = formData[field].filter((_: any, i: number) => i !== index)
    setFormData({...formData, [field]: newArray})
  }

  const updateField = (field: 'emails' | 'times' | 'symbols', index: number, value: string) => {
    const newArray = [...formData[field]]
    newArray[index] = value
    setFormData({...formData, [field]: newArray})
  }

  if (editMode) {
    return (
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3>⚙️ Edit Settings</h3>
          <div>
            <button onClick={() => setEditMode(false)} style={{ padding: '8px 16px', background: '#6c757d', color: 'white', border: 'none', borderRadius: 4, marginRight: 8 }}>
              Cancel
            </button>
            <button onClick={handleSave} style={{ padding: '8px 16px', background: '#28a745', color: 'white', border: 'none', borderRadius: 4 }}>
              Save Changes
            </button>
          </div>
        </div>
        
        <div style={{ display: 'grid', gap: 24 }}>
          {/* From Address */}
          <div style={{ padding: 16, background: '#f8f9fa', border: '1px solid #dee2e6', borderRadius: 8 }}>
            <h4 style={{ margin: '0 0 8px 0' }}>📧 From Address</h4>
            <p style={{ margin: '0 0 12px 0', color: '#666', fontSize: '14px' }}>
              Sender address for emails. Must be a verified domain in Resend (e.g., Market Intel &lt;digest@yourdomain.com&gt;)
            </p>
            <input 
              value={formData.email_from}
              onChange={e => setFormData({...formData, email_from: e.target.value})}
              placeholder="Market Intel <digest@yourdomain.com>"
              style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
            />
          </div>
          {/* Email Recipients */}
          <div className="card">
            <h4 style={{ margin: '0 0 8px 0' }}>📧 Email Recipients</h4>
            <p style={{ margin: '0 0 12px 0', color: '#666', fontSize: '14px' }}>
              Email addresses that will receive the daily market intelligence digest
            </p>
            {formData.emails.map((email: string, i: number) => (
              <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                <input 
                  type="email"
                  value={email} 
                  onChange={e => updateField('emails', i, e.target.value)}
                  placeholder="email@example.com"
                  style={{ flex: 1, padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
                />
                <button onClick={() => removeField('emails', i)} className="btn danger">×</button>
              </div>
            ))}
            <button onClick={() => addField('emails')} className="btn primary">+ Add Email</button>
          </div>

          {/* Digest Times */}
          <div className="card">
            <h4 style={{ margin: '0 0 8px 0' }}>🕐 Digest Send Times</h4>
            <p style={{ margin: '0 0 12px 0', color: '#666', fontSize: '14px' }}>
              Times of day to send digest emails (24-hour format, e.g., "06:30" for 6:30 AM)
            </p>
            {formData.times.map((time: string, i: number) => (
              <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                <input 
                  type="time"
                  value={time} 
                  onChange={e => updateField('times', i, e.target.value)}
                  style={{ flex: 1, padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
                />
                <button onClick={() => removeField('times', i)} className="btn danger">×</button>
              </div>
            ))}
            <button onClick={() => addField('times')} className="btn primary">+ Add Time</button>
          </div>

          {/* Watchlist */}
          <div className="card">
            <h4 style={{ margin: '0 0 8px 0' }}>📈 Market Watchlist</h4>
            <p style={{ margin: '0 0 12px 0', color: '#666', fontSize: '14px' }}>
              Stock symbols, ETFs, or keywords to prioritize in market news (e.g., AAPL, BTC, SPY)
            </p>
            {formData.symbols.map((symbol: string, i: number) => (
              <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                <input 
                  value={symbol} 
                  onChange={e => updateField('symbols', i, e.target.value.toUpperCase())}
                  placeholder="AAPL"
                  style={{ flex: 1, padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
                />
                <button onClick={() => removeField('symbols', i)} className="btn danger">×</button>
              </div>
            ))}
            <button onClick={() => addField('symbols')} className="btn primary">+ Add Symbol</button>
          </div>

          {/* Processing Settings */}
          <div className="card">
            <h4 style={{ margin: '0 0 16px 0' }}>⚙️ Processing Configuration</h4>
            
            <div style={{ display: 'grid', gap: 16 }}>
              <div>
                <label style={{ display: 'block', fontWeight: 'bold', marginBottom: 4 }}>Max Concurrency</label>
                <p style={{ margin: '0 0 8px 0', color: '#666', fontSize: '13px' }}>
                  How many RSS feeds to fetch simultaneously (higher = faster but more resource intensive)
                </p>
                <input 
                  type="number"
                  min="1"
                  max="20"
                  value={formData.max_concurrency} 
                  onChange={e => setFormData({...formData, max_concurrency: e.target.value})}
                  style={{ width: '100px', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontWeight: 'bold', marginBottom: 4 }}>Max Articles Considered</label>
                <p style={{ margin: '0 0 8px 0', color: '#666', fontSize: '13px' }}>
                  Total number of articles to evaluate from all feeds before filtering
                </p>
                <input 
                  type="number"
                  min="10"
                  max="500"
                  value={formData.max_articles_considered} 
                  onChange={e => setFormData({...formData, max_articles_considered: e.target.value})}
                  style={{ width: '100px', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontWeight: 'bold', marginBottom: 4 }}>Max Articles for AI</label>
                <p style={{ margin: '0 0 8px 0', color: '#666', fontSize: '13px' }}>
                  Maximum articles to send to AI for summarization (affects cost and processing time)
                </p>
                <input 
                  type="number"
                  min="5"
                  max="100"
                  value={formData.max_articles_for_ai} 
                  onChange={e => setFormData({...formData, max_articles_for_ai: e.target.value})}
                  style={{ width: '100px', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontWeight: 'bold', marginBottom: 4 }}>Per-Source Cap</label>
                <p style={{ margin: '0 0 8px 0', color: '#666', fontSize: '13px' }}>
                  Max number of articles per source in the ranked selection (diversity control)
                </p>
                <input 
                  type="number"
                  min="1"
                  max="50"
                  value={formData.per_source_cap} 
                  onChange={e => setFormData({...formData, per_source_cap: e.target.value})}
                  style={{ width: '100px', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontWeight: 'bold', marginBottom: 4 }}>Primary AI Provider</label>
                <p style={{ margin: '0 0 8px 0', color: '#666', fontSize: '13px' }}>
                  Choose your primary summarization provider (fallbacks will apply automatically)
                </p>
                <select value={formData.ai_primary} onChange={e => setFormData({...formData, ai_primary: e.target.value})} style={{ padding: 8, border: '1px solid #ddd', borderRadius: 4 }}>
                  <option value="gemini">Gemini</option>
                  <option value="openai">OpenAI</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontWeight: 'bold', marginBottom: 4 }}>Gemini Model ID</label>
                <input value={formData.gemini_model_id} onChange={e => setFormData({...formData, gemini_model_id: e.target.value})} style={{ width: '280px', padding: 8, border: '1px solid #ddd', borderRadius: 4 }} />
                <p className="muted">Default: gemini-2.5-flash</p>
              </div>

              <div>
                <label style={{ display: 'block', fontWeight: 'bold', marginBottom: 4 }}>OpenAI Model ID</label>
                <input value={formData.openai_model_id} onChange={e => setFormData({...formData, openai_model_id: e.target.value})} style={{ width: '280px', padding: 8, border: '1px solid #ddd', borderRadius: 4 }} />
                <p className="muted">Default: gpt-5-mini</p>
              </div>

              <div>
                <label style={{ display: 'block', fontWeight: 'bold', marginBottom: 4 }}>OpenAI Reasoning Effort</label>
                <select value={formData.openai_reasoning} onChange={e => setFormData({...formData, openai_reasoning: e.target.value})} style={{ padding: 8, border: '1px solid #ddd', borderRadius: 4 }}>
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Display mode
  return (
    <div>
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>⚙️ System Settings</h3>
        <button onClick={startEdit} className="btn primary">Edit Settings</button>
      </div>

      <div className="grid" style={{ gap: 16 }}>
        <div className="card">
          <h4>📧 Email Configuration</h4>
          <div><strong>Recipients:</strong> {parseJsonArray(settings.recipient_emails).join(', ') || 'None configured'}</div>
          <div><strong>Send Times:</strong> {parseJsonArray(settings.digest_times).join(', ') || 'None configured'}</div>
          <div><strong>From:</strong> {settings.email_from || 'Not set'}</div>
        </div>

        <div className="card">
          <h4>📈 Market Tracking</h4>
          <div><strong>Watchlist:</strong> {parseJsonArray(settings.watchlist).join(', ') || 'None configured'}</div>
        </div>

        <div className="card">
          <h4>⚙️ Processing Configuration</h4>
          <div><strong>Max Concurrency:</strong> {settings.max_concurrency || 'Not set'}</div>
          <div><strong>Max Articles Considered:</strong> {settings.max_articles_considered || 'Not set'}</div>
          <div><strong>Max Articles for AI:</strong> {settings.max_articles_for_ai || 'Not set'}</div>
          <div><strong>Per-Source Cap:</strong> {settings.per_source_cap || '10'}</div>
          <div><strong>Primary AI Provider:</strong> {settings.ai_primary || 'gemini'}</div>
          <div><strong>Gemini Model:</strong> {settings.gemini_model_id || 'gemini-2.5-flash'}</div>
          <div><strong>OpenAI Model:</strong> {settings.openai_model_id || 'gpt-4o-mini'}</div>
        </div>
      </div>
    </div>
  )
}

function Runs() {
  const [runs, setRuns] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [logView, setLogView] = useState<{runId: string, rows: any[]} | null>(null)

  useEffect(() => {
    getRuns(100).then(r => setRuns(r.runs || [])).finally(() => setLoading(false))
  }, [])

  const openLogs = async (runId: string) => {
    const r = await getRunLogs(runId)
    setLogView({ runId, rows: r.logs || [] })
  }

  if (loading) return <div className="card">Loading...</div>

  return (
    <div>
      <h3 style={{ margin: '4px 0 12px' }}>Runs & Archive</h3>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Run ID</th>
              <th>Status</th>
              <th>Started</th>
              <th>Finished</th>
              <th style={{ textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r:any) => (
              <tr key={r.run_id}>
                <td style={{ fontFamily: 'monospace' }}>{r.run_id}</td>
                <td>{r.status}</td>
                <td>{r.started_at ? new Date(r.started_at).toLocaleString() : ''}</td>
                <td>{r.finished_at ? new Date(r.finished_at).toLocaleString() : ''}</td>
                <td style={{ textAlign: 'center' }}>
                  <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
                    <a href={getRunDigestUrl(r.run_id)} target="_blank" rel="noreferrer" className="button-link"><button className="btn primary">View Digest</button></a>
                    <button onClick={() => openLogs(r.run_id)} className="btn">View Logs</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {logView && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={() => setLogView(null)}>
          <div className="card" style={{ width: '90%', maxWidth: 900, maxHeight: '80%', overflow: 'auto' }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <h4 style={{ margin: 0 }}>Logs for {logView.runId}</h4>
              <button onClick={() => setLogView(null)} className="btn">Close</button>
            </div>
            <pre style={{ whiteSpace: 'pre-wrap' }}>
{logView.rows.map((row:any) => `${new Date(row.ts).toLocaleString()} [${row.level}] ${row.message}${row.context_json? ' ' + row.context_json : ''}`).join('\n')}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

function PromptEditor() {
  const [loading, setLoading] = useState(true)
  const [value, setValue] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getPrompt().then((r:any)=>{
      // API now returns { prompt: effective, custom }
      setValue(r.prompt || defaultPrompt)
    }).finally(()=>setLoading(false))
  }, [])

  const save = async () => {
    setSaving(true)
    try {
      await updatePrompt(value)
      alert('Prompt saved')
    } catch (e) {
      alert('Failed to save prompt')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="card">Loading...</div>

  return (
    <div>
      <h3 style={{ margin: '4px 0 12px' }}>Prompt Editor</h3>
      <div className="card">
        <p className="muted">Customize the summarization prompt. The watchlist and headlines are appended automatically.</p>
        <textarea value={value} onChange={e=>setValue(e.target.value)} style={{ width: '100%', minHeight: 300, padding: 12, border: '1px solid #ddd', borderRadius: 6, fontFamily: 'monospace' }} />
        <div style={{ marginTop: 10, display: 'flex', gap: 8 }}>
          <button onClick={save} disabled={saving} className="btn success">{saving ? 'Saving…' : 'Save Prompt'}</button>
          <button onClick={()=>setValue(defaultPrompt)} className="btn">Reset to Default</button>
        </div>
      </div>
    </div>
  )
}

const defaultPrompt = `You are a professional financial analyst creating a comprehensive market intelligence report.

Generate a structured report with exactly these sections:

## SECTION 1 - MARKET PERFORMANCE
[Market data will be injected here - you analyze the implications]
Provide a 3-4 sentence overarching market summary explaining what the price movements mean.

## SECTION 2 - TOP MARKET & ECONOMY STORIES (5 stories)
Select the 5 most important financial/economic stories. For each:
**Story Title**: [Headline]
[Write 4-6 sentences explaining the story, its market implications, and context]
Sources: [List relevant source URLs]

## SECTION 3 - GENERAL NEWS STORIES (10 stories)
Select 10 other significant news stories. For each:
**Story Title**: [Headline]
[Write 2-3 sentences summarizing the story and any broader implications]
Sources: [List relevant source URLs]

IMPORTANT:
- Use specific company names, tickers, and numbers when available
- Focus on market impact and investor implications
- Each story must cite actual sources from the provided articles
- Write in professional, analytical tone`
