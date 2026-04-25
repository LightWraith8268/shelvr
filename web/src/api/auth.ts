import { apiFetch, apiJson, setAccessToken, setRefreshToken } from './client'

export interface CurrentUser {
  id: number
  username: string
  role: string
  is_active: boolean
  created_at: string
  last_login_at: string | null
}

interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export class LoginError extends Error {}

export async function login(username: string, password: string): Promise<CurrentUser> {
  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (response.status === 401) throw new LoginError('Invalid username or password')
  if (!response.ok) throw new LoginError(`Login failed (HTTP ${response.status})`)
  const body = (await response.json()) as TokenResponse
  setAccessToken(body.access_token)
  setRefreshToken(body.refresh_token)
  return await fetchMe()
}

export async function fetchMe(): Promise<CurrentUser> {
  return apiJson<CurrentUser>('/api/v1/auth/me')
}

export async function logout(refreshToken: string | null): Promise<void> {
  if (refreshToken) {
    await apiFetch('/api/v1/auth/logout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
  }
}

export class PasswordChangeError extends Error {}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  const response = await apiFetch('/api/v1/auth/me/password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  })
  if (response.status === 400) {
    throw new PasswordChangeError('Current password is incorrect.')
  }
  if (response.status === 422) {
    throw new PasswordChangeError('New password must be at least 8 characters.')
  }
  if (!response.ok) {
    throw new PasswordChangeError(`Password change failed (HTTP ${response.status}).`)
  }
}
