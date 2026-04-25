import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  type CurrentUser,
  fetchMe,
  login as loginRequest,
  logout as logoutRequest,
} from '../api/auth'
import {
  clearTokens,
  getRefreshToken,
  setAccessToken,
  setOnAuthLost,
} from '../api/client'

type AuthStatus = 'loading' | 'unauthenticated' | 'authenticated'

interface AuthState {
  status: AuthStatus
  user: CurrentUser | null
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<CurrentUser | null>(null)

  const handleAuthLost = useCallback(() => {
    setUser(null)
    setStatus('unauthenticated')
  }, [])

  useEffect(() => {
    setOnAuthLost(handleAuthLost)
    return () => setOnAuthLost(null)
  }, [handleAuthLost])

  // On mount: if a refresh token exists, try to bootstrap the session.
  useEffect(() => {
    let cancelled = false
    async function bootstrap() {
      if (!getRefreshToken()) {
        if (!cancelled) setStatus('unauthenticated')
        return
      }
      try {
        const me = await fetchMe()
        if (!cancelled) {
          setUser(me)
          setStatus('authenticated')
        }
      } catch {
        if (!cancelled) {
          clearTokens()
          setStatus('unauthenticated')
        }
      }
    }
    bootstrap()
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const me = await loginRequest(username, password)
    setUser(me)
    setStatus('authenticated')
  }, [])

  const logout = useCallback(async () => {
    const refresh = getRefreshToken()
    try {
      await logoutRequest(refresh)
    } finally {
      clearTokens()
      setAccessToken(null)
      setUser(null)
      setStatus('unauthenticated')
    }
  }, [])

  const value = useMemo<AuthState>(
    () => ({ status, user, login, logout }),
    [status, user, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
