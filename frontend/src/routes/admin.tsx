import { createFileRoute } from '@tanstack/react-router'
import { useState, useDeferredValue } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { AdminRoute } from '../components/AdminRoute'
import { Topbar } from '../components/Topbar'
import { ConfirmDialog } from '../components/ConfirmDialog'

export const Route = createFileRoute('/admin')({
  component: () => (
    <AdminRoute>
      <AdminDashboardPage />
    </AdminRoute>
  ),
})

interface DashboardMetrics {
  total_users: number
  active_sessions: number
  mfa_enabled_users: number
  failed_login_attempts_24h: number
}

interface UserRow {
  id: string
  username: string
  email: string
  created_at: string
  is_locked: boolean
}

interface OAuthClient {
  id: string
  name: string
  redirect_uris: string[]
  scopes: string[]
  is_confidential: boolean
  is_active: boolean
}

const card: React.CSSProperties = {
  background: 'var(--color-card)',
  border: '1px solid var(--color-border)',
  borderRadius: '10px',
  padding: '24px',
}

const sectionTitle: React.CSSProperties = {
  color: 'var(--color-text)',
  fontSize: '16px',
  fontWeight: 600,
  marginBottom: '16px',
}

function MetricTile({ label, value }: { label: string; value: number }) {
  return (
    <div
      style={{
        ...card,
        textAlign: 'center',
        flex: '1 1 180px',
        minWidth: '150px',
      }}
    >
      <div style={{ color: 'var(--color-accent)', fontSize: '28px', fontWeight: 700 }}>{value}</div>
      <div style={{ color: 'var(--color-text-muted)', fontSize: '13px', marginTop: '4px' }}>
        {label}
      </div>
    </div>
  )
}

function AdminDashboardPage() {
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const deferredSearch = useDeferredValue(search)
  const [confirm, setConfirm] = useState<{ type: 'lock' | 'unlock' | 'delete'; userId: string } | null>(null)

  const { data: metrics } = useQuery({
    queryKey: ['admin-metrics'],
    queryFn: () => api.get<DashboardMetrics>('/admin/dashboard').then((r) => r.data),
  })

  const { data: usersData } = useQuery({
    queryKey: ['admin-users', page, deferredSearch],
    queryFn: () =>
      api
        .get<{ users: UserRow[]; total: number; page: number; limit: number }>(
          `/admin/users?page=${page}&limit=20&search=${encodeURIComponent(deferredSearch)}`,
        )
        .then((r) => r.data),
  })

  const { data: clients } = useQuery({
    queryKey: ['oauth-clients'],
    queryFn: () => api.get<OAuthClient[]>('/admin/oauth/clients').then((r) => r.data),
  })

  const lockUser = useMutation({
    mutationFn: (id: string) => api.post(`/admin/users/${id}/lock`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-users'] }); setConfirm(null) },
  })

  const unlockUser = useMutation({
    mutationFn: (id: string) => api.post(`/admin/users/${id}/unlock`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-users'] }); setConfirm(null) },
  })

  const deleteUser = useMutation({
    mutationFn: (id: string) => api.delete(`/admin/users/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-users'] }); setConfirm(null) },
  })

  const revokeClient = useMutation({
    mutationFn: (id: string) => api.delete(`/admin/oauth/clients/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['oauth-clients'] }),
  })

  function handleConfirm() {
    if (!confirm) return
    if (confirm.type === 'lock') lockUser.mutate(confirm.userId)
    else if (confirm.type === 'unlock') unlockUser.mutate(confirm.userId)
    else deleteUser.mutate(confirm.userId)
  }

  return (
    <div style={{ minHeight: '100svh', background: 'var(--color-bg)' }}>
      <Topbar />
      {confirm && (
        <ConfirmDialog
          message={
            confirm.type === 'delete'
              ? 'Permanently delete this user? This cannot be undone.'
              : `${confirm.type === 'lock' ? 'Lock' : 'Unlock'} this user account?`
          }
          onConfirm={handleConfirm}
          onCancel={() => setConfirm(null)}
        />
      )}

      <div
        style={{
          maxWidth: '1100px',
          margin: '0 auto',
          padding: '32px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '24px',
        }}
      >
        {/* Metrics */}
        {metrics && (
          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
            <MetricTile label="Total users" value={metrics.total_users} />
            <MetricTile label="Active sessions" value={metrics.active_sessions} />
            <MetricTile label="MFA enabled" value={metrics.mfa_enabled_users} />
            <MetricTile label="Failed logins (24h)" value={metrics.failed_login_attempts_24h} />
          </div>
        )}

        {/* Users */}
        <div style={card}>
          <p style={sectionTitle}>Users</p>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
            <input
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              placeholder="Search username or email…"
              style={{
                background: 'var(--color-bg)',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                color: 'var(--color-text)',
                fontSize: '14px',
                padding: '8px 12px',
                width: '280px',
              }}
            />
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-muted)' }}>
                {['Username', 'Email', 'Created', 'Status', 'Actions'].map((h) => (
                  <th key={h} style={{ textAlign: 'left', padding: '8px 12px', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {usersData?.users.map((u) => (
                <tr
                  key={u.id}
                  style={{ borderBottom: '1px solid var(--color-border)', color: 'var(--color-text)' }}
                >
                  <td style={{ padding: '10px 12px' }}>{u.username}</td>
                  <td style={{ padding: '10px 12px' }}>{u.email}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--color-text-muted)' }}>
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    {u.is_locked ? (
                      <span style={{ color: 'var(--color-error-text)', fontSize: '12px' }}>Locked</span>
                    ) : (
                      <span style={{ color: 'var(--color-success-text)', fontSize: '12px' }}>Active</span>
                    )}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      {u.is_locked ? (
                        <ActionBtn onClick={() => setConfirm({ type: 'unlock', userId: u.id })}>Unlock</ActionBtn>
                      ) : (
                        <ActionBtn onClick={() => setConfirm({ type: 'lock', userId: u.id })}>Lock</ActionBtn>
                      )}
                      <ActionBtn
                        onClick={() => setConfirm({ type: 'delete', userId: u.id })}
                        danger
                      >
                        Delete
                      </ActionBtn>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {usersData && usersData.total > 20 && (
            <div style={{ display: 'flex', gap: '8px', marginTop: '16px', justifyContent: 'flex-end' }}>
              <PageBtn disabled={page === 1} onClick={() => setPage((p) => p - 1)}>← Prev</PageBtn>
              <span style={{ color: 'var(--color-text-muted)', fontSize: '13px', alignSelf: 'center' }}>
                Page {page} of {Math.ceil(usersData.total / 20)}
              </span>
              <PageBtn
                disabled={page * 20 >= usersData.total}
                onClick={() => setPage((p) => p + 1)}
              >
                Next →
              </PageBtn>
            </div>
          )}
        </div>

        {/* OAuth clients */}
        <div style={card}>
          <p style={sectionTitle}>OAuth clients</p>
          {clients && clients.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {clients.map((c) => (
                <div
                  key={c.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: 'var(--color-bg)',
                    border: '1px solid var(--color-border)',
                    borderRadius: '6px',
                    padding: '12px 16px',
                  }}
                >
                  <div>
                    <div style={{ color: 'var(--color-text)', fontWeight: 600, fontSize: '14px' }}>
                      {c.name}
                    </div>
                    <div style={{ color: 'var(--color-text-muted)', fontSize: '12px', marginTop: '2px' }}>
                      Scopes: {c.scopes.join(', ')} · {c.is_confidential ? 'Confidential' : 'Public'}
                    </div>
                  </div>
                  <ActionBtn onClick={() => revokeClient.mutate(c.id)} danger>
                    Revoke
                  </ActionBtn>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--color-text-muted)', fontSize: '14px' }}>No OAuth clients registered.</p>
          )}
        </div>
      </div>
    </div>
  )
}

function ActionBtn({
  children,
  onClick,
  danger,
}: {
  children: React.ReactNode
  onClick: () => void
  danger?: boolean
}) {
  return (
    <button
      onClick={onClick}
      style={{
        background: 'transparent',
        border: `1px solid ${danger ? 'var(--color-error-border)' : 'var(--color-border)'}`,
        borderRadius: '5px',
        color: danger ? 'var(--color-error-text)' : 'var(--color-text-muted)',
        cursor: 'pointer',
        fontSize: '12px',
        padding: '4px 10px',
      }}
    >
      {children}
    </button>
  )
}

function PageBtn({
  children,
  onClick,
  disabled,
}: {
  children: React.ReactNode
  onClick: () => void
  disabled: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        background: 'transparent',
        border: '1px solid var(--color-border)',
        borderRadius: '5px',
        color: disabled ? 'var(--color-border)' : 'var(--color-text-muted)',
        cursor: disabled ? 'default' : 'pointer',
        fontSize: '13px',
        padding: '5px 12px',
      }}
    >
      {children}
    </button>
  )
}
