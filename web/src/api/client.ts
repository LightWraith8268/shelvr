/**
 * Central fetch wrapper. Injects the bearer access token and transparently
 * refreshes it once on 401 before retrying the request.
 *
 * Tokens:
 *   - access:  in memory only (lost on reload)
 *   - refresh: localStorage (required for session survival across reloads)
 *
 * The refresh token in localStorage is reachable by XSS, but Shelvr is
 * self-hosted and serves only first-party content; refresh tokens are
 * revocable from the server (logout / admin reset). Document this tradeoff
 * here so it isn't relitigated.
 */

const REFRESH_STORAGE_KEY = 'shelvr.refresh_token'

let accessToken: string | null = null
let refreshInflight: Promise<boolean> | null = null
let onAuthLost: (() => void) | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

export function setRefreshToken(token: string | null): void {
  if (token) {
    localStorage.setItem(REFRESH_STORAGE_KEY, token)
  } else {
    localStorage.removeItem(REFRESH_STORAGE_KEY)
  }
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_STORAGE_KEY)
}

export function clearTokens(): void {
  accessToken = null
  setRefreshToken(null)
}

/**
 * Register a callback fired when refresh fails — gives the AuthProvider a
 * chance to redirect to /login and reset its own state.
 */
export function setOnAuthLost(callback: (() => void) | null): void {
  onAuthLost = callback
}

async function attemptRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false

  const response = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!response.ok) {
    clearTokens()
    onAuthLost?.()
    return false
  }
  const body = (await response.json()) as { access_token: string; refresh_token: string }
  setAccessToken(body.access_token)
  setRefreshToken(body.refresh_token)
  return true
}

async function ensureRefreshInflight(): Promise<boolean> {
  if (refreshInflight) return refreshInflight
  refreshInflight = attemptRefresh().finally(() => {
    refreshInflight = null
  })
  return refreshInflight
}

function buildHeaders(init: RequestInit | undefined): Headers {
  const headers = new Headers(init?.headers)
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  return headers
}

/**
 * Fetch wrapper. Returns the Response. Caller is responsible for parsing JSON
 * or checking ``response.ok`` — keeping this thin makes it composable with
 * TanStack Query.
 */
export async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  const firstAttempt = await fetch(input, { ...init, headers: buildHeaders(init) })
  if (firstAttempt.status !== 401) return firstAttempt

  const refreshed = await ensureRefreshInflight()
  if (!refreshed) return firstAttempt

  return fetch(input, { ...init, headers: buildHeaders(init) })
}

export async function apiJson<T>(input: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(input, init)
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return (await response.json()) as T
}
