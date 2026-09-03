import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { ADMIN_TOKEN_STORAGE_KEY, fetchCurrentAdmin, loginAdmin } from '../api/adminApi'
import type { AdminUser } from '../api/adminApi'

interface AdminAuthContextValue {
  admin: AdminUser | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refreshAdmin: () => Promise<void>
}

const AdminAuthContext = createContext<AdminAuthContextValue | null>(null)

export function AdminAuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => window.sessionStorage.getItem(ADMIN_TOKEN_STORAGE_KEY))
  const [admin, setAdmin] = useState<AdminUser | null>(null)
  const [loading, setLoading] = useState(Boolean(token))

  const clearAuth = useCallback(() => {
    window.sessionStorage.removeItem(ADMIN_TOKEN_STORAGE_KEY)
    setToken(null)
    setAdmin(null)
  }, [])

  const refreshAdmin = useCallback(async () => {
    if (!window.sessionStorage.getItem(ADMIN_TOKEN_STORAGE_KEY)) {
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const current = await fetchCurrentAdmin()
      setAdmin(current)
    } catch {
      clearAuth()
    } finally {
      setLoading(false)
    }
  }, [clearAuth])

  useEffect(() => {
    void refreshAdmin()
  }, [refreshAdmin])

  useEffect(() => {
    window.addEventListener('admin-auth-expired', clearAuth)
    return () => window.removeEventListener('admin-auth-expired', clearAuth)
  }, [clearAuth])

  const login = useCallback(async (email: string, password: string) => {
    const response = await loginAdmin(email, password)
    window.sessionStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, response.access_token)
    setToken(response.access_token)
    const current = await fetchCurrentAdmin()
    setAdmin(current)
  }, [])

  const value = useMemo(
    () => ({ admin, token, loading, login, logout: clearAuth, refreshAdmin }),
    [admin, token, loading, login, clearAuth, refreshAdmin],
  )

  return <AdminAuthContext.Provider value={value}>{children}</AdminAuthContext.Provider>
}

export function useAdminAuth(): AdminAuthContextValue {
  const context = useContext(AdminAuthContext)
  if (!context) throw new Error('useAdminAuth must be used within AdminAuthProvider')
  return context
}
