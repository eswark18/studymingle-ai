import { useCallback, useEffect, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import TurnstileWidget from './TurnstileWidget'
import './ProductionGate.css'

type Availability = 'checking' | 'online' | 'maintenance'

type Props = {
  children: ReactNode
}

const deploymentMode = import.meta.env.VITE_DEPLOYMENT_MODE ?? 'local'
const apiBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export default function ProductionGate({ children }: Props) {
  const [availability, setAvailability] = useState<Availability>(
    deploymentMode === 'production' ? 'checking' : 'online',
  )
  const [turnstileToken, setTurnstileToken] = useState('')
  const [formError, setFormError] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const onToken = useCallback((token: string) => setTurnstileToken(token), [])
  const onTurnstileError = useCallback((message: string) => setFormError(message), [])

  useEffect(() => {
    if (deploymentMode !== 'production') return

    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 8000)

    fetch(`${apiBase}/health`, {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
      signal: controller.signal,
    })
      .then((response) => {
        setAvailability(response.ok ? 'online' : 'maintenance')
      })
      .catch(() => setAvailability('maintenance'))
      .finally(() => window.clearTimeout(timeout))

    return () => {
      window.clearTimeout(timeout)
      controller.abort()
    }
  }, [])

  async function requestDemo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const fields = new FormData(form)
    setSubmitting(true)
    setFormError('')

    try {
      const response = await fetch('/api/demo-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: fields.get('name'),
          email: fields.get('email'),
          preferred_time: fields.get('preferredTime'),
          audience: fields.get('audience'),
          message: fields.get('message'),
          company: fields.get('company'),
          turnstile_token: turnstileToken,
        }),
      })
      const payload = await response.json().catch(() => null) as { message?: string } | null
      if (!response.ok) throw new Error(payload?.message ?? 'Your request could not be sent.')
      form.reset()
      setSubmitted(true)
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Your request could not be sent.')
    } finally {
      setSubmitting(false)
    }
  }

  if (availability === 'online') return children

  return (
    <main className="availability-page">
      <a className="availability-brand" href="https://thoughtmingle.com" aria-label="StudyMingle by ThoughtMingle">
        <span className="availability-mark">✦</span>
        <span>Study<span>Mingle</span></span>
        <small>AI</small>
      </a>

      {availability === 'checking' ? (
        <section className="availability-check" aria-live="polite">
          <span className="availability-pulse" />
          <p>Checking whether the guided learning workspace is online…</p>
        </section>
      ) : (
        <div className="availability-layout">
          <section className="availability-message">
            <span className="availability-kicker">SCHEDULED DEMONSTRATION</span>
            <h1>The study coach is taking a short break.</h1>
            <p>
              StudyMingle currently runs as a private, locally hosted learning demonstration.
              Request a session and we’ll arrange a time for your student or group to try the complete workspace.
            </p>
            <div className="availability-points">
              <span><b>01</b> Upload a worksheet</span>
              <span><b>02</b> Review extracted questions</span>
              <span><b>03</b> Learn through guided explanations</span>
            </div>
            <aside>
              <strong>Already scheduled?</strong>
              <p>Return at your confirmed session time. The workspace will open automatically once the private tutor is online.</p>
              <button type="button" onClick={() => window.location.reload()}>Check again</button>
            </aside>
          </section>

          <section className="demo-request-card">
            <span className="availability-kicker">REQUEST ACCESS</span>
            <h2>Plan a private demo</h2>
            <p>Tell us who the session is for. We’ll reply with availability, duration, and any applicable fee.</p>
            {submitted ? (
              <div className="request-success" role="status">
                <span>✓</span>
                <h3>Request received</h3>
                <p>Thank you. We’ll reply by email to arrange your StudyMingle session.</p>
                <button type="button" onClick={() => setSubmitted(false)}>Send another request</button>
              </div>
            ) : (
              <form onSubmit={requestDemo}>
                <label><span>Name</span><input name="name" autoComplete="name" minLength={2} maxLength={120} required /></label>
                <label><span>Email</span><input name="email" type="email" autoComplete="email" maxLength={254} required /></label>
                <div className="request-row">
                  <label><span>Preferred date and time</span><input name="preferredTime" type="datetime-local" required /></label>
                  <label><span>Student or group</span><select name="audience" defaultValue="one-student"><option value="one-student">One student</option><option value="family">Family</option><option value="small-group">Small group</option><option value="school-or-college">School or college</option></select></label>
                </div>
                <label><span>What would you like to explore?</span><textarea name="message" maxLength={1000} rows={4} placeholder="Grade/year, subject, number of students, or any questions…" /></label>
                <label className="request-honeypot" aria-hidden="true"><span>Company</span><input name="company" tabIndex={-1} autoComplete="off" /></label>
                <TurnstileWidget action="demo_request" onToken={onToken} onError={onTurnstileError} />
                {formError && <p className="request-error" role="alert">{formError}</p>}
                <button className="request-submit" type="submit" disabled={submitting}>{submitting ? 'Sending…' : 'Request a demo session'} <span>→</span></button>
                <small>By submitting, you agree that ThoughtMingle may contact you about this request. No worksheet is uploaded through this form.</small>
              </form>
            )}
          </section>
        </div>
      )}
      <footer className="availability-footer">A ThoughtMingle learning prototype · Local-first · Privacy-aware</footer>
    </main>
  )
}
