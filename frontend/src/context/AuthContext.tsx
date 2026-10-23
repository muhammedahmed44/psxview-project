import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { authApi, type User } from '../api'

interface AuthValue {
  user: User | null
  checking: boolean // true until the first /me answer arrives
  setUser: (u: User | null) => void
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthValue>({
  user: null,
  checking: true,
  setUser: () => {},
  logout: async () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [checking, setChecking] = useState(true)

  // On page load, ask the server "am I logged in?" (the cookie answers).
  useEffect(() => {
    authApi
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setChecking(false))
  }, [])

  const logout = useCallback(async () => {
    await authApi.logout().catch(() => {})
    setUser(null)
  }, [])

  return <AuthContext.Provider value={{ user, checking, setUser, logout }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)