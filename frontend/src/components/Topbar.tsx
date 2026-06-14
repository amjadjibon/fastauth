import { Link } from '@tanstack/react-router'
import { useAuth } from '../contexts/AuthContext'

export function Topbar() {
  const { user, logout } = useAuth()

  async function handleLogout() {
    await logout()
    window.location.href = '/login'
  }

  return (
    <nav
      style={{
        background: 'var(--color-card)',
        borderBottom: '1px solid var(--color-border)',
        padding: '0 24px',
        height: '56px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
        <span
          style={{ color: 'var(--color-accent)', fontWeight: 700, fontSize: '18px', letterSpacing: '-0.3px' }}
        >
          FastAuth
        </span>
        <Link
          to="/dashboard"
          style={{ color: 'var(--color-text-muted)', textDecoration: 'none', fontSize: '14px' }}
        >
          Dashboard
        </Link>
        {user?.roles.includes('admin') && (
          <Link
            to="/admin"
            style={{ color: 'var(--color-text-muted)', textDecoration: 'none', fontSize: '14px' }}
          >
            Admin
          </Link>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ color: 'var(--color-text-muted)', fontSize: '14px' }}>{user?.username}</span>
        <button
          onClick={handleLogout}
          style={{
            background: 'transparent',
            border: '1px solid var(--color-border)',
            borderRadius: '6px',
            color: 'var(--color-text-muted)',
            cursor: 'pointer',
            fontSize: '13px',
            padding: '6px 12px',
          }}
        >
          Sign out
        </button>
      </div>
    </nav>
  )
}
