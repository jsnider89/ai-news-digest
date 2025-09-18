import React, { useEffect, useMemo, useState } from 'react'
import { NewsletterDetail, NewsletterFeedInput, NewsletterFormValues } from '../lib/api'

interface NewsletterFormProps {
  initial?: NewsletterDetail | null
  onSubmit: (values: NewsletterFormValues) => Promise<void>
  onCancel: () => void
  submitting: boolean
  timezoneOptions: Array<{ value: string; label: string }>
  defaultTimezone: string
}

type FeedField = NewsletterFeedInput & { enabled: boolean }

const slugify = (raw: string) =>
  raw
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')

const validateTime = (value: string) => /^([01]\d|2[0-3]):[0-5]\d$/.test(value)

export const NewsletterForm: React.FC<NewsletterFormProps> = ({ initial, onSubmit, onCancel, submitting, timezoneOptions, defaultTimezone }) => {
  const isEditing = Boolean(initial)
  const [name, setName] = useState(initial?.name ?? '')
  const [slug, setSlug] = useState(initial?.slug ?? '')
  const [timezone, setTimezone] = useState(initial?.timezone ?? defaultTimezone)
  const [customTimezone, setCustomTimezone] = useState('')
  const [useCustomTimezone, setUseCustomTimezone] = useState(() => {
    const tz = initial?.timezone ?? defaultTimezone
    return timezoneOptions.length > 0 ? !timezoneOptions.some((option) => option.value === tz) : true
  })
  const [scheduleText, setScheduleText] = useState((initial?.schedule_times ?? ['08:00']).join('\n'))
  const [includeWatchlist, setIncludeWatchlist] = useState(initial?.include_watchlist ?? false)
  const [watchlistText, setWatchlistText] = useState(initial?.watchlist_symbols?.join(', ') ?? '')
  const [newsletterType, setNewsletterType] = useState(initial?.newsletter_type ?? 'general_business')
  const [verbosityLevel, setVerbosityLevel] = useState(initial?.verbosity_level ?? 'medium')
  const [customPrompt, setCustomPrompt] = useState(initial?.custom_prompt ?? '')
  const [active, setActive] = useState(initial?.active ?? true)
  const [feeds, setFeeds] = useState<FeedField[]>(
    initial?.feeds && initial.feeds.length
      ? initial.feeds.map((feed) => ({
          url: feed.url,
          title: feed.title ?? '',
          category: feed.category ?? '',
          enabled: feed.enabled ?? true,
        }))
      : [
          {
            url: '',
            title: '',
            category: '',
            enabled: true,
          },
        ],
  )
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isEditing) {
      // Always update slug as user types the name
      setSlug(slugify(name))
    }
  }, [name, isEditing])

  useEffect(() => {
    if (initial) {
      const effectiveTimezone = initial.timezone || defaultTimezone
      setName(initial.name)
      setSlug(initial.slug)
      setTimezone(effectiveTimezone)
      setScheduleText(initial.schedule_times.join('\n'))
      setIncludeWatchlist(initial.include_watchlist)
      setWatchlistText(initial.watchlist_symbols.join(', '))
      setNewsletterType(initial.newsletter_type ?? 'general_business')
      setVerbosityLevel(initial.verbosity_level ?? 'medium')
      setCustomPrompt(initial.custom_prompt)
      setActive(initial.active)
      setFeeds(
        initial.feeds.length
          ? initial.feeds.map((feed) => ({
              url: feed.url,
              title: feed.title ?? '',
              category: feed.category ?? '',
              enabled: feed.enabled ?? true,
            }))
          : [{ url: '', title: '', category: '', enabled: true }],
      )
      const hasOption = timezoneOptions.some((option) => option.value === effectiveTimezone)
      setUseCustomTimezone(!hasOption)
      setCustomTimezone(!hasOption ? effectiveTimezone : '')
    } else {
      const effectiveTimezone = defaultTimezone
      setName('')
      setSlug('')
      setTimezone(effectiveTimezone)
      setScheduleText('08:00')
      setIncludeWatchlist(false)
      setWatchlistText('')
      setNewsletterType('general_business')
      setVerbosityLevel('medium')
      setCustomPrompt('')
      setActive(true)
      setFeeds([{ url: '', title: '', category: '', enabled: true }])
      const hasOption = timezoneOptions.some((option) => option.value === effectiveTimezone)
      setUseCustomTimezone(!hasOption)
      setCustomTimezone(!hasOption ? effectiveTimezone : '')
    }
    setError(null)
  }, [initial, timezoneOptions, defaultTimezone])

  const scheduleTimes = useMemo(
    () =>
      scheduleText
        .split(/[,\n]/)
        .map((entry) => entry.trim())
        .filter(Boolean),
    [scheduleText],
  )

  const watchlistSymbols = useMemo(
    () =>
      watchlistText
        .split(/[,\s]+/)
        .map((entry) => entry.trim().toUpperCase())
        .filter(Boolean),
    [watchlistText],
  )

  const preparedFeeds = useMemo(
    () =>
      feeds
        .map((feed) => ({
          ...feed,
          url: feed.url.trim(),
          title: feed.title?.trim() || undefined,
          category: feed.category?.trim() || undefined,
          enabled: feed.enabled,
        }))
        .filter((feed) => feed.url.length > 0),
    [feeds],
  )

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError('Name is required.')
      return
    }

    // Ensure slug is generated from name if empty
    const finalSlug = slug.trim() || slugify(name.trim())

    if (!finalSlug || !/^[a-z0-9-]+$/.test(finalSlug)) {
      setError('Slug must contain only lowercase letters, numbers, and hyphens.')
      return
    }

    const effectiveTimezone = (useCustomTimezone ? customTimezone : timezone).trim()

    if (!effectiveTimezone) {
      setError('Timezone is required.')
      return
    }

    if (scheduleTimes.length === 0) {
      setError('Configure at least one scheduled send time (HH:MM).')
      return
    }

    if (!scheduleTimes.every(validateTime)) {
      setError('Scheduled times must be in HH:MM (24h) format.')
      return
    }

    if (preparedFeeds.length === 0) {
      setError('Add at least one feed URL for the newsletter.')
      return
    }

    const payload: NewsletterFormValues = {
      slug: finalSlug,
      name: name.trim(),
      timezone: effectiveTimezone,
      schedule_times: scheduleTimes,
      include_watchlist: includeWatchlist,
      newsletter_type: newsletterType,
      verbosity_level: verbosityLevel,
      custom_prompt: customPrompt.trim(),
      feeds: preparedFeeds,
      watchlist_symbols: includeWatchlist ? watchlistSymbols : [],
      active,
    }

    try {
      await onSubmit(payload)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to save newsletter.')
    }
  }

  const updateFeed = <K extends keyof FeedField>(index: number, key: K, value: FeedField[K]) => {
    setFeeds((current) => current.map((feed, i) => (i === index ? { ...feed, [key]: value } : feed)))
  }

  const addFeedRow = () => {
    setFeeds((current) => [...current, { url: '', title: '', category: '', enabled: true }])
  }

  const removeFeedRow = (index: number) => {
    setFeeds((current) => (current.length <= 1 ? current : current.filter((_, i) => i !== index)))
  }

  const hasTimezoneOptions = timezoneOptions.length > 0

  return (
    <form onSubmit={handleSubmit} className="form-grid">
      {error && <div className="alert">{error}</div>}
      <div className="form-grid two">
        <div className="form-field">
          <label htmlFor="newsletter-name">Newsletter Name</label>
          <input
            id="newsletter-name"
            value={name}
            autoFocus
            onChange={(event) => setName(event.target.value)}
            placeholder="Morning Market Pulse"
          />
          <span className="form-helper">Visible label in dashboards and email subject lines.</span>
        </div>
        <div className="form-field">
          <label htmlFor="newsletter-slug">Slug (auto-generated)</label>
          <input
            id="newsletter-slug"
            value={slug}
            disabled={true}
            placeholder="will-be-generated-from-name"
          />
          <span className="form-helper">Auto-generated from newsletter name. Used in URLs and scheduling.</span>
        </div>
      </div>

      <div className="form-grid two">
        <div className="form-field">
          <label htmlFor="newsletter-timezone">Timezone</label>
          {hasTimezoneOptions ? (
            <>
              <select
                id="newsletter-timezone"
                value={useCustomTimezone ? '__custom' : timezone}
                onChange={(event) => {
                  const value = event.target.value
                  if (value === '__custom') {
                    setUseCustomTimezone(true)
                    setCustomTimezone('')
                  } else {
                    setUseCustomTimezone(false)
                    setTimezone(value)
                  }
                }}
              >
                {timezoneOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
                <option value="__custom">Custom…</option>
              </select>
              {useCustomTimezone && (
                <input
                  id="newsletter-timezone-custom"
                  value={customTimezone}
                  onChange={(event) => setCustomTimezone(event.target.value)}
                  placeholder="America/Denver"
                  style={{ marginTop: 8 }}
                />
              )}
            </>
          ) : (
            <input
              id="newsletter-timezone"
              value={timezone}
              onChange={(event) => setTimezone(event.target.value)}
              placeholder="America/New_York"
            />
          )}
          <span className="form-helper">Choose a timezone (IANA name, e.g., America/Denver).</span>
        </div>
        <div className="form-field">
          <label htmlFor="newsletter-times">Send Times</label>
          <textarea
            id="newsletter-times"
            value={scheduleText}
            onChange={(event) => setScheduleText(event.target.value)}
            placeholder={'08:00\n16:00'}
          />
          <span className="form-helper">Enter one HH:MM per line for scheduled digests.</span>
        </div>
      </div>

      <div className="form-field">
        <label>Feeds</label>
        <div className="form-helper">Provide RSS or Atom feed URLs.</div>
        <div className="form-grid">
          {feeds.map((feed, index) => (
            <div key={index} className="card" style={{ padding: 16 }}>
              <div className="form-field">
                <label htmlFor={`feed-url-${index}`}>Feed URL</label>
                <input
                  id={`feed-url-${index}`}
                  value={feed.url}
                  onChange={(event) => updateFeed(index, 'url', event.target.value)}
                  placeholder="https://example.com/rss"
                  required
                />
              </div>
              <div className="form-grid two">
                <div className="form-field">
                  <label htmlFor={`feed-title-${index}`}>Display Title</label>
                  <input
                    id={`feed-title-${index}`}
                    value={feed.title ?? ''}
                    onChange={(event) => updateFeed(index, 'title', event.target.value)}
                    placeholder="Bloomberg Markets"
                  />
                </div>
                <div className="form-field">
                  <label htmlFor={`feed-category-${index}`}>Category</label>
                  <input
                    id={`feed-category-${index}`}
                    value={feed.category ?? ''}
                    onChange={(event) => updateFeed(index, 'category', event.target.value)}
                    placeholder="Macro"
                  />
                </div>
              </div>
              <div className="form-field">
                <label htmlFor={`feed-enabled-${index}`} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input
                    id={`feed-enabled-${index}`}
                    type="checkbox"
                    checked={feed.enabled !== false}
                    onChange={(event) => updateFeed(index, 'enabled', event.target.checked)}
                  />
                  Enabled
                </label>
                <span className="form-helper">Disabled feeds stay saved but are skipped during runs.</span>
              </div>
              <div className="button-row" style={{ justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  className="btn danger"
                  onClick={() => removeFeedRow(index)}
                  disabled={feeds.length <= 1}
                >
                  Remove Feed
                </button>
              </div>
            </div>
          ))}
        </div>
        <div className="button-row">
          <button type="button" className="btn" onClick={addFeedRow}>
            Add Feed
          </button>
        </div>
      </div>

      <div className="form-grid two">
        <div className="form-field">
          <label htmlFor="watchlist-toggle">Include Watchlist</label>
          <select
            id="watchlist-toggle"
            value={includeWatchlist ? 'yes' : 'no'}
            onChange={(event) => setIncludeWatchlist(event.target.value === 'yes')}
          >
            <option value="no">Disabled</option>
            <option value="yes">Enabled</option>
          </select>
          <span className="form-helper">If enabled, tickers are surfaced to the AI prompt and email.</span>
        </div>
        <div className="form-field">
          <label htmlFor="watchlist-symbols">Watchlist Symbols</label>
          <textarea
            id="watchlist-symbols"
            value={watchlistText}
            onChange={(event) => setWatchlistText(event.target.value)}
            placeholder="AAPL, MSFT, NVDA"
            disabled={!includeWatchlist}
          />
          <span className="form-helper">Comma or space separated ticker symbols.</span>
        </div>
      </div>

      <div className="form-grid two">
        <div className="form-field">
          <label htmlFor="newsletter-type">Newsletter Type</label>
          <select
            id="newsletter-type"
            value={newsletterType}
            onChange={(event) => setNewsletterType(event.target.value)}
          >
            <option value="general_business">General Business</option>
            <option value="tech_focus">Tech Focus</option>
            <option value="market_pulse">Market Pulse</option>
            <option value="general_news">General News</option>
            <option value="industry_specific">Industry Specific</option>
          </select>
          <span className="form-helper">Choose the primary content focus for this newsletter.</span>
        </div>
        <div className="form-field">
          <label htmlFor="verbosity-level">Verbosity Level</label>
          <select
            id="verbosity-level"
            value={verbosityLevel}
            onChange={(event) => setVerbosityLevel(event.target.value)}
          >
            <option value="low">Low (Concise)</option>
            <option value="medium">Medium (Balanced)</option>
            <option value="high">High (Detailed)</option>
          </select>
          <span className="form-helper">Controls the length and detail level of AI-generated content.</span>
        </div>
      </div>

      <div className="form-field">
        <label htmlFor="custom-prompt">Custom Prompt</label>
        <textarea
          id="custom-prompt"
          value={customPrompt}
          onChange={(event) => setCustomPrompt(event.target.value)}
          placeholder="Add any newsletter-specific instructions for the AI summary."
        />
        <span className="form-helper">Optional additional instructions that supplement the selected newsletter type.</span>
      </div>

      {isEditing && (
        <div className="form-field">
          <label htmlFor="newsletter-active">Status</label>
          <select id="newsletter-active" value={active ? 'active' : 'paused'} onChange={(event) => setActive(event.target.value === 'active')}>
            <option value="active">Active (scheduled)</option>
            <option value="paused">Paused</option>
          </select>
        </div>
      )}

      <div className="dialog-actions">
        <button type="button" className="btn" onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
        <button type="submit" className="btn primary" disabled={submitting}>
          {submitting ? 'Saving…' : isEditing ? 'Update Newsletter' : 'Create Newsletter'}
        </button>
      </div>
    </form>
  )
}
