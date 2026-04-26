import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  changePassword,
  changeUsername,
  PasswordChangeError,
  UsernameChangeError,
} from '../api/auth'
import { useAuth } from '../auth/AuthProvider'
import { clearTokens } from '../api/client'

export function AccountView() {
  const { user, logout, refresh } = useAuth()
  const queryClient = useQueryClient()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwSuccess, setPwSuccess] = useState<string | null>(null)
  const [isSubmittingPw, setIsSubmittingPw] = useState(false)

  const [usernameInput, setUsernameInput] = useState('')
  const [usernamePassword, setUsernamePassword] = useState('')
  const [unameError, setUnameError] = useState<string | null>(null)
  const [unameSuccess, setUnameSuccess] = useState<string | null>(null)
  const [isSubmittingUname, setIsSubmittingUname] = useState(false)

  useEffect(() => {
    if (user && !usernameInput) setUsernameInput(user.username)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user])

  async function handlePasswordSubmit(event: FormEvent) {
    event.preventDefault()
    setPwError(null)
    setPwSuccess(null)

    if (newPassword !== confirmPassword) {
      setPwError('New password and confirmation do not match.')
      return
    }
    if (newPassword.length < 8) {
      setPwError('New password must be at least 8 characters.')
      return
    }

    setIsSubmittingPw(true)
    try {
      await changePassword(currentPassword, newPassword)
      clearTokens()
      setPwSuccess('Password changed. Please sign in again.')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setTimeout(() => {
        logout()
      }, 1500)
    } catch (caught) {
      setPwError(
        caught instanceof PasswordChangeError ? caught.message : 'Password change failed.',
      )
    } finally {
      setIsSubmittingPw(false)
    }
  }

  async function handleUsernameSubmit(event: FormEvent) {
    event.preventDefault()
    setUnameError(null)
    setUnameSuccess(null)

    const trimmed = usernameInput.trim()
    if (!trimmed) {
      setUnameError('Username must not be blank.')
      return
    }

    setIsSubmittingUname(true)
    try {
      const updated = await changeUsername(usernamePassword, trimmed)
      setUnameSuccess(`Username changed to ${updated.username}.`)
      setUsernamePassword('')
      // Push the new user into AuthProvider so the header updates immediately.
      await refresh()
      queryClient.invalidateQueries({ queryKey: ['me'] })
    } catch (caught) {
      setUnameError(
        caught instanceof UsernameChangeError ? caught.message : 'Username change failed.',
      )
    } finally {
      setIsSubmittingUname(false)
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

      <h3 className="text-sm font-medium text-slate-700">Change username</h3>
      <form onSubmit={handleUsernameSubmit} className="mt-3 space-y-3">
        <Field label="New username">
          <input
            type="text"
            autoComplete="username"
            required
            value={usernameInput}
            onChange={(event) => setUsernameInput(event.target.value)}
            className={inputClass}
          />
        </Field>
        <Field label="Current password">
          <input
            type="password"
            autoComplete="current-password"
            required
            value={usernamePassword}
            onChange={(event) => setUsernamePassword(event.target.value)}
            className={inputClass}
          />
        </Field>
        {unameError && (
          <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {unameError}
          </p>
        )}
        {unameSuccess && (
          <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {unameSuccess}
          </p>
        )}
        <button
          type="submit"
          disabled={isSubmittingUname}
          className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800 disabled:opacity-50"
        >
          {isSubmittingUname ? 'Saving…' : 'Change username'}
        </button>
      </form>

      <h3 className="mt-8 text-sm font-medium text-slate-700">Change password</h3>
      <form onSubmit={handlePasswordSubmit} className="mt-3 space-y-3">
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

        {pwError && (
          <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {pwError}
          </p>
        )}
        {pwSuccess && (
          <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {pwSuccess}
          </p>
        )}

        <button
          type="submit"
          disabled={isSubmittingPw}
          className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800 disabled:opacity-50"
        >
          {isSubmittingPw ? 'Changing…' : 'Change password'}
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
