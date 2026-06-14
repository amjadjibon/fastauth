import { createFileRoute, Link } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { AuthCard, styles } from '../components/AuthCard'

export const Route = createFileRoute('/verify-email')({
  validateSearch: (s: Record<string, unknown>) => ({ token: (s.token as string) ?? '' }),
  component: VerifyEmailPage,
})

function VerifyEmailPage() {
  const { token } = Route.useSearch()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage('No verification token provided.')
      return
    }
    api
      .post('/auth/verify-email', { token })
      .then(() => setStatus('success'))
      .catch((err: unknown) => {
        const detail =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Verification failed. The link may have expired.'
        setStatus('error')
        setMessage(detail)
      })
  }, [token])

  return (
    <AuthCard title="Email verification">
      {status === 'loading' && (
        <p style={{ color: 'var(--color-text-muted)', textAlign: 'center' }}>Verifying…</p>
      )}
      {status === 'success' && (
        <>
          <p style={{ color: 'var(--color-success-text)', textAlign: 'center', fontSize: '15px' }}>
            Your email has been verified. You can now sign in.
          </p>
          <div style={{ ...styles.footer, marginTop: '20px' }}>
            <Link to="/login" style={styles.link}>
              Sign in
            </Link>
          </div>
        </>
      )}
      {status === 'error' && (
        <p style={{ color: 'var(--color-error-text)', textAlign: 'center', fontSize: '15px' }}>
          {message}
        </p>
      )}
    </AuthCard>
  )
}
