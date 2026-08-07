import { useCallback, useState } from 'react'
import type { FormEvent } from 'react'
import { apiRequest } from '../auth'
import type { AuthMode, AuthUser } from '../auth'
import TurnstileWidget from './TurnstileWidget'

type Props = {
  initialMode: AuthMode
  onAuthenticated: (user: AuthUser) => void
  onClose: () => void
}

export default function AuthModal({ initialMode, onAuthenticated, onClose }: Props) {
  const [mode, setMode] = useState<AuthMode>(initialMode)
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const onToken = useCallback((value: string) => setToken(value), [])
  const onTurnstileError = useCallback((message: string) => setError(message), [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setSubmitting(true)
    setError('')
    try {
      const payload = mode === 'register'
        ? {
            email: form.get('email'),
            password: form.get('password'),
            display_name: form.get('displayName'),
            education_track: form.get('educationTrack'),
            grade_or_year: form.get('gradeOrYear'),
            turnstile_token: token || null,
          }
        : {
            email: form.get('email'),
            password: form.get('password'),
            turnstile_token: token || null,
          }
      const user = await apiRequest<AuthUser>(`/auth/${mode === 'register' ? 'register' : 'login'}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      onAuthenticated(user)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to continue. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  function changeMode(nextMode: AuthMode) {
    setMode(nextMode)
    setError('')
    setToken('')
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose()
    }}>
      <section className="auth-modal" role="dialog" aria-modal="true" aria-labelledby="auth-title">
        <button className="modal-close" type="button" onClick={onClose} aria-label="Close">×</button>
        <span className="kicker">YOUR LEARNING SPACE</span>
        <h2 id="auth-title">{mode === 'register' ? 'Create your account' : 'Welcome back'}</h2>
        <p>{mode === 'register'
          ? 'Save your learning profile and continue from any device.'
          : 'Sign in to return to your guided workspace.'}</p>
        <div className="auth-tabs" role="tablist" aria-label="Account access">
          <button type="button" className={mode === 'login' ? 'active' : ''} onClick={() => changeMode('login')}>Sign in</button>
          <button type="button" className={mode === 'register' ? 'active' : ''} onClick={() => changeMode('register')}>Create account</button>
        </div>
        <form className="auth-form" onSubmit={submit}>
          {mode === 'register' && (
            <>
              <label><span>Name</span><input name="displayName" autoComplete="name" minLength={2} maxLength={120} required /></label>
              <div className="auth-row">
                <label><span>Learning track</span><select name="educationTrack" defaultValue="school"><option value="school">School</option><option value="engineering">Engineering</option></select></label>
                <label><span>Grade or year</span><input name="gradeOrYear" maxLength={32} placeholder="Grade 8" /></label>
              </div>
            </>
          )}
          <label><span>Email</span><input name="email" type="email" autoComplete="email" maxLength={254} required /></label>
          <label><span>Password</span><input name="password" type="password" autoComplete={mode === 'register' ? 'new-password' : 'current-password'} minLength={mode === 'register' ? 12 : 1} maxLength={128} required /><small>{mode === 'register' ? 'Use at least 12 characters with a letter and number.' : ''}</small></label>
          <TurnstileWidget onToken={onToken} onError={onTurnstileError} />
          {error && <p className="form-alert" role="alert">{error}</p>}
          <button className="primary-button full" type="submit" disabled={submitting}>
            {submitting ? 'Please wait…' : mode === 'register' ? 'Create account' : 'Sign in'}
          </button>
        </form>
      </section>
    </div>
  )
}
