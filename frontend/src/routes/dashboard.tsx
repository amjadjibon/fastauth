import { createFileRoute, Link } from '@tanstack/react-router'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useAuth } from '../contexts/AuthContext'
import { ProtectedRoute } from '../components/ProtectedRoute'
import { Topbar } from '../components/Topbar'
import { FormError } from '../components/FormError'
import { styles } from '../components/AuthCard'

const card: React.CSSProperties = {
  background: 'var(--color-card)',
  border: '1px solid var(--color-border)',
  borderRadius: '10px',
  padding: '24px',
}

const pageStyle: React.CSSProperties = {
  minHeight: '100svh',
  background: 'var(--color-bg)',
}

const body: React.CSSProperties = {
  maxWidth: '900px',
  margin: '0 auto',
  padding: '32px 24px',
  display: 'flex',
  flexDirection: 'column',
  gap: '24px',
}

const sectionTitle: React.CSSProperties = {
  color: 'var(--color-text)',
  fontSize: '16px',
  fontWeight: 600,
  marginBottom: '16px',
}

const badge = (color: string): React.CSSProperties => ({
  display: 'inline-block',
  background: color,
  borderRadius: '4px',
  padding: '2px 8px',
  fontSize: '12px',
  fontWeight: 600,
  color: '#fff',
})

// ---------- Change password form ----------
const pwSchema = z.object({
  current_password: z.string().min(1, 'Required'),
  new_password: z
    .string()
    .min(8, 'At least 8 characters')
    .regex(/[A-Z]/, 'Needs an uppercase letter')
    .regex(/[0-9]/, 'Needs a number'),
})
type PwForm = z.infer<typeof pwSchema>

interface SessionItem {
  id: string
  browser: string | null
  os: string | null
  ip_address: string | null
  last_active_at: string | null
  is_current: boolean
}

export const Route = createFileRoute('/dashboard')({
  component: () => (
    <ProtectedRoute>
      <DashboardPage />
    </ProtectedRoute>
  ),
})

function DashboardPage() {
  const { user } = useAuth()
  const qc = useQueryClient()
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwSuccess, setPwSuccess] = useState(false)

  const { data: sessions } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => api.get<{ sessions: SessionItem[] }>('/auth/sessions').then((r) => r.data.sessions),
  })

  const { data: mfaStatus } = useQuery({
    queryKey: ['mfa-status'],
    queryFn: () => api.get<{ enabled: boolean }>('/auth/mfa/status').then((r) => r.data),
  })

  const revokeSession = useMutation({
    mutationFn: (id: string) => api.delete(`/auth/sessions/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  })

  const {
    register: regPw,
    handleSubmit: handlePw,
    reset: resetPw,
    formState: { errors: pwErrors, isSubmitting: pwSubmitting },
  } = useForm<PwForm>({ resolver: zodResolver(pwSchema) })

  async function onChangePassword(data: PwForm) {
    setPwError(null)
    setPwSuccess(false)
    try {
      await api.post('/auth/change-password', data)
      resetPw()
      setPwSuccess(true)
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed'
      setPwError(detail)
    }
  }

  return (
    <div style={pageStyle}>
      <Topbar />
      <div style={body}>
        {/* Profile */}
        <div style={card}>
          <p style={sectionTitle}>Profile</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <Row label="Username" value={user?.username} />
            <Row label="Email" value={user?.email} />
            <Row
              label="Email verified"
              value={
                user?.email_verified ? (
                  <span style={badge('var(--color-success-border)')}>Verified</span>
                ) : (
                  <span style={badge('var(--color-error-border)')}>Not verified</span>
                )
              }
            />
            <Row
              label="Roles"
              value={user?.roles.map((r) => (
                <span key={r} style={{ ...badge('var(--color-accent)'), marginRight: '4px' }}>
                  {r}
                </span>
              ))}
            />
          </div>
        </div>

        {/* Sessions */}
        <div style={card}>
          <p style={sectionTitle}>Active sessions</p>
          {sessions && sessions.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {sessions.map((s) => (
                <div
                  key={s.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 14px',
                    background: 'var(--color-bg)',
                    borderRadius: '6px',
                    border: '1px solid var(--color-border)',
                  }}
                >
                  <div>
                    <span style={{ color: 'var(--color-text)', fontSize: '14px' }}>
                      {[s.browser, s.os].filter(Boolean).join(' · ') || 'Unknown device'}
                    </span>
                    {s.is_current && (
                      <span style={{ ...badge('var(--color-accent)'), marginLeft: '8px', fontSize: '11px' }}>
                        Current
                      </span>
                    )}
                    <div style={{ color: 'var(--color-text-muted)', fontSize: '12px', marginTop: '2px' }}>
                      {s.ip_address} · Last active{' '}
                      {s.last_active_at ? new Date(s.last_active_at).toLocaleString() : 'unknown'}
                    </div>
                  </div>
                  {!s.is_current && (
                    <button
                      onClick={() => revokeSession.mutate(s.id)}
                      style={{
                        background: 'transparent',
                        border: '1px solid var(--color-error-border)',
                        borderRadius: '5px',
                        color: 'var(--color-error-text)',
                        cursor: 'pointer',
                        fontSize: '12px',
                        padding: '4px 10px',
                      }}
                    >
                      Revoke
                    </button>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--color-text-muted)', fontSize: '14px' }}>No active sessions.</p>
          )}
        </div>

        {/* MFA */}
        <div style={card}>
          <p style={sectionTitle}>Two-factor authentication</p>
          {mfaStatus?.enabled ? (
            <p style={{ color: 'var(--color-text-muted)', fontSize: '14px' }}>
              MFA is <span style={badge('var(--color-success-border)')}>Enabled</span>
            </p>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <p style={{ color: 'var(--color-text-muted)', fontSize: '14px' }}>MFA is not enabled.</p>
              <Link
                to="/dashboard/mfa"
                style={{
                  ...styles.link,
                  background: 'var(--color-accent)',
                  color: '#fff',
                  borderRadius: '6px',
                  padding: '6px 14px',
                  fontSize: '13px',
                  fontWeight: 600,
                  textDecoration: 'none',
                }}
              >
                Enable MFA
              </Link>
            </div>
          )}
        </div>

        {/* Change password */}
        <div style={card}>
          <p style={sectionTitle}>Change password</p>
          <form
            onSubmit={handlePw(onChangePassword)}
            style={{ ...styles.form, maxWidth: '380px' }}
          >
            <FormError message={pwError} />
            {pwSuccess && (
              <p style={{ color: 'var(--color-success-text)', fontSize: '14px' }}>
                Password changed successfully.
              </p>
            )}
            <div style={styles.field}>
              <label style={styles.label}>Current password</label>
              <input {...regPw('current_password')} type="password" style={styles.input} />
              {pwErrors.current_password && (
                <span style={styles.fieldError}>{pwErrors.current_password.message}</span>
              )}
            </div>
            <div style={styles.field}>
              <label style={styles.label}>New password</label>
              <input {...regPw('new_password')} type="password" style={styles.input} />
              {pwErrors.new_password && (
                <span style={styles.fieldError}>{pwErrors.new_password.message}</span>
              )}
            </div>
            <button type="submit" disabled={pwSubmitting} style={{ ...styles.submitBtn, width: 'auto', padding: '10px 20px' }}>
              {pwSubmitting ? 'Saving…' : 'Change password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
      <span style={{ color: 'var(--color-text-muted)', fontSize: '14px', minWidth: '120px' }}>
        {label}
      </span>
      <span style={{ color: 'var(--color-text)', fontSize: '14px' }}>{value}</span>
    </div>
  )
}
