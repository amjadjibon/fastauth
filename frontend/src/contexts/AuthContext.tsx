import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { api } from '../lib/api'
import { clearTokens, getTokens, setTokens } from '../lib/tokens'

export interface User {
  id: string
  username: string
  email: string
  email_verified: boolean
  roles: string[]
  permissions: string[]
  created_at: string
  updated_at: string
}

interface AuthState {
  user: User | null
  isLoading: boolean
  login: (username: string, password: string) => Promise<LoginResult>
  logout: () => Promise<void>
  setUser: (user: User | null) => void
}

export interface LoginResult {
  mfa_required: boolean
  mfa_session_token?: string
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const { accessToken } = getTokens()
    if (!accessToken) {
      setIsLoading(false)
      return
    }
    api
      .get<User>('/auth/me')
      .then((res) => setUser(res.data))
      .catch(() => clearTokens())
      .finally(() => setIsLoading(false))
  }, [])

  const login = useCallback(
    async (username: string, password: string): Promise<LoginResult> => {
      const res = await api.post<{
        access_token: string | null
        refresh_token: string | null
        mfa_required: boolean
        mfa_session_token?: string
      }>('/auth/login', { username, password })

      const { access_token, refresh_token, mfa_required, mfa_session_token } = res.data

      if (mfa_required) {
        return { mfa_required: true, mfa_session_token }
      }

      if (access_token && refresh_token) {
        setTokens(access_token, refresh_token)
        const me = await api.get<User>('/auth/me')
        setUser(me.data)
      }

      return { mfa_required: false }
    },
    [],
  )

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      // best-effort revocation
    }
    clearTokens()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
