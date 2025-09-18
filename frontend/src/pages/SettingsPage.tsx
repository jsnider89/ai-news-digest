import React, { useEffect, useState } from 'react'
import { getSettings, updateSettings, SettingsResponse, MetaOptions } from '../lib/api'

const formatList = (values: string[]) => values.join(', ')

interface SettingsPageProps {
  meta: MetaOptions | null
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ meta }) => {
  const [settings, setSettings] = useState<SettingsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [timezone, setTimezone] = useState('')
  const [sendTimes, setSendTimes] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [primaryModel, setPrimaryModel] = useState('')
  const [secondaryModel, setSecondaryModel] = useState('')
  const [reasoningLevel, setReasoningLevel] = useState('medium')
  const [recipients, setRecipients] = useState('')

  const load = async () => {
    try {
      setLoading(true)
      const data = await getSettings()
      setSettings(data)
      setTimezone(data.default_timezone)
      setSendTimes(data.default_send_times.join('\n'))
      setPrimaryModel(data.primary_model)
      setSecondaryModel(data.secondary_model || '')
      setReasoningLevel(data.reasoning_level)
      setRecipients(data.default_recipients.join('\n'))
      setError(null)
    } catch (err) {
      console.error(err)
      setError(err instanceof Error ? err.message : 'Failed to load settings.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  useEffect(() => {
    if (!message) return
    const timeout = window.setTimeout(() => setMessage(null), 4000)
    return () => window.clearTimeout(timeout)
  }, [message])

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setMessage(null)
    try {
      const filteredTimes = sendTimes
        .split(/[,\n]/)
        .map((entry) => entry.trim())
        .filter(Boolean)
      const recipientList = recipients
        .split(/[,\n]/)
        .map((entry) => entry.trim())
        .filter(Boolean)

      const payload = {
        default_timezone: timezone.trim() || undefined,
        default_send_times: filteredTimes.length ? filteredTimes : undefined,
        primary_model: primaryModel || undefined,
        secondary_model: secondaryModel && secondaryModel !== primaryModel ? secondaryModel : undefined,
        reasoning_level: reasoningLevel || undefined,
        default_recipients: recipientList,
      }

      const updated = await updateSettings(payload)
      setSettings(updated)
      setPrimaryModel(updated.primary_model)
      setSecondaryModel(updated.secondary_model || '')
      setReasoningLevel(updated.reasoning_level)
      setRecipients(updated.default_recipients.join('\n'))
      setMessage('Settings saved successfully.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save settings.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page settings">
      <div className="card" style={{ marginBottom: 24 }}>
        <h3 className="section-title">Global Defaults</h3>
        <p className="lead">These values seed new newsletters and configure the AI + email stack.</p>
      </div>

      {error && <div className="alert">{error}</div>}
      {message && <div className="toast">{message}</div>}

      {loading && !settings ? (
        <div className="spinner" aria-busy />
      ) : (
        <div className="card">
          <form onSubmit={handleSubmit} className="form-grid">
            <div className="form-grid two">
              <div className="form-field">
                <label htmlFor="default-timezone">Default Timezone</label>
                {meta?.timezones && meta.timezones.length > 0 ? (
                  <select
                    id="default-timezone"
                    value={timezone}
                    onChange={(event) => setTimezone(event.target.value)}
                  >
                    {!meta.timezones.some((option) => option.value === timezone) && (
                      <option value={timezone}>{timezone}</option>
                    )}
                    {meta.timezones.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    id="default-timezone"
                    value={timezone}
                    onChange={(event) => setTimezone(event.target.value)}
                    placeholder="America/New_York"
                  />
                )}
                <span className="form-helper">Used when a newsletter does not specify a timezone.</span>
              </div>
              <div className="form-field">
                <label htmlFor="default-times">Default Send Times</label>
                <textarea
                  id="default-times"
                  value={sendTimes}
                  onChange={(event) => setSendTimes(event.target.value)}
                  placeholder={'08:00\n16:00'}
                />
                <span className="form-helper">Times applied to new newsletters (one HH:MM per line).</span>
              </div>
            </div>

            <hr className="divider" />

            <div className="form-grid two">
              <div className="form-field">
                <label htmlFor="primary-model">Primary Model</label>
                <select
                  id="primary-model"
                  value={primaryModel}
                  onChange={(event) => {
                    const value = event.target.value
                    setPrimaryModel(value)
                    if (value === secondaryModel) {
                      setSecondaryModel('')
                    }
                    const selected = meta?.models.find((option) => option.value === value)
                    if (selected && !selected.supports_reasoning) {
                      setReasoningLevel('medium')
                    }
                  }}
                >
                  {meta?.models?.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  )) || <option value={primaryModel}>{primaryModel || 'Select model'}</option>}
                </select>
                <span className="form-helper">Primary provider used for each digest.</span>
              </div>

              <div className="form-field">
                <label htmlFor="secondary-model">Secondary Model (fallback)</label>
                <select
                  id="secondary-model"
                  value={secondaryModel}
                  onChange={(event) => setSecondaryModel(event.target.value)}
                >
                  <option value="">— None —</option>
                  {meta?.models?.map((option) => (
                    <option key={option.value} value={option.value} disabled={option.value === primaryModel}>
                      {option.label}
                    </option>
                  )) || <option value={secondaryModel}>{secondaryModel || 'Select model'}</option>}
                </select>
                <span className="form-helper">Used if the primary provider fails.</span>
              </div>
            </div>

            <div className="form-grid two">
              <div className="form-field">
                <label htmlFor="reasoning-level">Reasoning Level</label>
                <select
                  id="reasoning-level"
                  value={reasoningLevel}
                  onChange={(event) => setReasoningLevel(event.target.value)}
                  disabled={!meta?.models?.find((option) => option.value === primaryModel)?.supports_reasoning}
                >
                  {meta?.reasoning_levels?.map((level) => (
                    <option key={level} value={level}>
                      {level.charAt(0).toUpperCase() + level.slice(1)}
                    </option>
                  )) || ['low', 'medium', 'high'].map((level) => (
                    <option key={level} value={level}>
                      {level.charAt(0).toUpperCase() + level.slice(1)}
                    </option>
                  ))}
                </select>
                <span className="form-helper">Applies to OpenAI models that support structured reasoning.</span>
              </div>

              <div className="form-field">
                <label htmlFor="default-recipients">Recipients</label>
                <textarea
                  id="default-recipients"
                  value={recipients}
                  onChange={(event) => setRecipients(event.target.value)}
                  placeholder={'alice@example.com\nbob@example.com'}
                />
                <span className="form-helper">Comma or newline separated addresses for automated sends.</span>
              </div>
            </div>

            <div className="dialog-actions">
              <button type="submit" className="btn primary" disabled={saving}>
                {saving ? 'Saving…' : 'Save Defaults'}
              </button>
            </div>
          </form>
        </div>
      )}

      {settings && (
        <div className="card" style={{ marginTop: 24 }}>
          <h3 className="section-title">AI &amp; Email Configuration</h3>
          <div className="form-grid two">
            <div>
              <h4>Primary Model</h4>
              <div className="muted">{settings.primary_model}</div>
            </div>
            <div>
              <h4>Secondary Model</h4>
              <div className="muted">{settings.secondary_model || 'None'}</div>
            </div>
            <div>
              <h4>Reasoning Level</h4>
              <div className="muted">{settings.reasoning_level}</div>
            </div>
            <div>
              <h4>Resend Sender</h4>
              <div className="muted">{settings.resend_from_name} &lt;{settings.resend_from_email}&gt;</div>
            </div>
            <div>
              <h4>Recipients</h4>
              <div className="muted">{settings.default_recipients.length ? formatList(settings.default_recipients) : 'Not configured'}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
