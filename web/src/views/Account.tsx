import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { changePassword, PasswordChangeError } from '../api/auth'
import { useAuth } from '../auth/AuthProvider'
import { clearTokens } from '../api/client'

export function AccountView() {
  const { user, logout } = useAuth()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setErrorMessage(null)
    setSuccessMessage(null)

    if (newPassword !== confirmPassword) {
      setErrorMessage('New password and confirmation do not match.')
      return
    }
    if (newPassword.length < 8) {
      setErrorMessage('New password must be at least 8 characters.')
      return
    }

    setIsSubmitting(true)
    try {
      await changePassword(currentPassword, newPassword)
      // Server revokes all refresh tokens on rotation. Drop local state and
      // route the user to /login so they sign in again with the new password.
      clearTokens()
      setSuccessMessage('Password changed. Please sign in again.')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      // Trigger logout-driven redirect once user reads the message.
      setTimeout(() => {
        logout()
      }, 1500)
    } catch (caught) {
      setErrorMessage(
        caught instanceof PasswordChangeError ? caught.message : 'Password change failed.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="max-w-md">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold tracking-tight">Account</h2>
        <Link to="/" className="text-sm text-slate-500 hover:text-slate-900">
          ← Back to library
        </Link>
      </div>

      {user && (
        <dl className="mb-6 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-slate-500">Username</dt>
          <dd className="font-mono">{user.username}</dd>
          <dt className="text-slate-500">Role</dt>
          <dd>{user.role}</dd>
        </dl>
      )}

      <h3 className="text-sm font-medium text-slate-700">Change password</h3>
      <form onSubmit={handleSubmit} className="mt-3 space-y-3">
        <Field label="Current password">
          <input
            type="password"
            autoComplete="current-password"
            required
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            className={inputClass}
          />
        </Field>
        <Field label="New password (8+ characters)">
          <input
            type="password"
            autoComplete="new-password"
            minLength={8}
            required
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            className={inputClass}
          />
        </Field>
        <Field label="Confirm new password">
          <input
            type="password"
            autoComplete="new-password"
            minLength={8}
            required
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            className={inputClass}
          />
        </Field>

        {errorMessage && (
          <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {errorMessage}
          </p>
        )}
        {successMessage && (
          <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {successMessage}
          </p>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800 disabled:opacity-50"
        >
          {isSubmitting ? 'Changing…' : 'Change password'}
        </button>
      </form>
    </section>
  )
}

const inputClass =
  'mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-slate-500">{label}</span>
      <span className="mt-1 block">{children}</span>
    </label>
  )
}
