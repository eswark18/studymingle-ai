import { useState } from 'react'
import type { FormEvent } from 'react'
import { apiRequest } from '../auth'
import type { AuthUser } from '../auth'

type Props = {
  user: AuthUser
  onClose: () => void
  onDeleted: () => void
}

export default function AccountModal({ user, onClose, onDeleted }: Props) {
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function deleteAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setSubmitting(true)
    setError('')
    try {
      await apiRequest<void>('/auth/account', {
        method: 'DELETE',
        body: JSON.stringify({ password: form.get('password') }),
      })
      onDeleted()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Account deletion failed.')
      setSubmitting(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose()
    }}>
      <section className="auth-modal account-modal" role="dialog" aria-modal="true" aria-labelledby="account-title">
        <button className="modal-close" type="button" onClick={onClose} aria-label="Close">×</button>
        <span className="kicker">ACCOUNT</span>
        <h2 id="account-title">Your learning profile</h2>
        <dl className="profile-details">
          <div><dt>Name</dt><dd>{user.display_name ?? 'Not provided'}</dd></div>
          <div><dt>Email</dt><dd>{user.email}</dd></div>
          <div><dt>Track</dt><dd>{user.education_track ?? 'Not selected'}</dd></div>
          <div><dt>Grade or year</dt><dd>{user.grade_or_year ?? 'Not selected'}</dd></div>
        </dl>
        <div className="danger-zone">
          <h3>Delete account</h3>
          <p>This anonymizes your profile and immediately revokes every active session.</p>
          {!confirming ? (
            <button className="danger-button" type="button" onClick={() => setConfirming(true)}>Delete my account</button>
          ) : (
            <form className="delete-form" onSubmit={deleteAccount}>
              <label><span>Confirm your password</span><input name="password" type="password" autoComplete="current-password" required /></label>
              {error && <p className="form-alert" role="alert">{error}</p>}
              <div><button className="text-button" type="button" onClick={() => setConfirming(false)}>Cancel</button><button className="danger-button" type="submit" disabled={submitting}>{submitting ? 'Deleting…' : 'Delete permanently'}</button></div>
            </form>
          )}
        </div>
      </section>
    </div>
  )
}
