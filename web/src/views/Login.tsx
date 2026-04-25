import { useState } from 'react'
import type { FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { LoginError } from '../api/auth'
import { useAuth } from '../auth/AuthProvider'

interface LocationState {
  from?: { pathname: string }
}

export function LoginView() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setErrorMessage(null)
    setIsSubmitting(true)
    try {
      await login(username, password)
      const target = (location.state as LocationState | null)?.from?.pathname ?? '/'
      navigate(target, { replace: true })
    } catch (caught) {
      if (caught instanceof LoginError) {
        setErrorMessage(caught.message)
      } else {
        setErrorMessage('Login failed.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <h2 className="text-xl font-semibold tracking-tight">Sign in</h2>
      <form onSubmit={handleSubmit} className="mt-4 space-y-3">
        <div>
          <label className="block text-xs font-medium text-slate-500" htmlFor="login-username">
            Username
          </label>
          <input
            id="login-username"
            type="text"
            autoComplete="username"
            autoFocus
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
            required
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500" htmlFor="login-password">
            Password
          </label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
            required
          />
        </div>
        {errorMessage && (
          <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {errorMessage}
          </p>
        )}
        <button
          type="submit"
          disabled={isSubmitting || !username || !password}
          className="w-full rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800 disabled:opacity-50"
        >
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
      <p className="mt-3 text-xs text-slate-500">
        Need an account? Run <code className="font-mono">shelvr user create &lt;username&gt;</code>{' '}
        on the server.
      </p>
    </div>
  )
}
