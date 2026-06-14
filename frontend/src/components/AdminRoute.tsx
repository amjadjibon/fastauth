import { Navigate } from '@tanstack/react-router'
import type { ReactNode } from 'react'
import { useAuth } from '../contexts/AuthContext'

export function AdminRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return null
  if (!user) return <Navigate to="/login" />
  if (!user.roles.includes('admin')) return <Navigate to="/dashboard" />
  return <>{children}</>
}
