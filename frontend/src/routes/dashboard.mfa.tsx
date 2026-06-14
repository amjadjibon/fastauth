import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect, useRef, useState } from 'react'
import QRCode from 'qrcode'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api } from '../lib/api'
import { ProtectedRoute } from '../components/ProtectedRoute'
import { Topbar } from '../components/Topbar'
import { FormError } from '../components/FormError'
import { styles } from '../components/AuthCard'

const schema = z.object({ code: z.string().min(6, 'Enter the 6-digit code from your app') })
type FormData = z.infer<typeof schema>

export const Route = createFileRoute('/dashboard/mfa')({
  component: () => (
    <ProtectedRoute>
      <MfaSetupPage />
    </ProtectedRoute>
  ),
})

interface SetupData {
  secret: string
  qr_code_uri: string
  backup_codes: string[]
}

function MfaSetupPage() {
  const navigate = useNavigate()
  const [setup, setSetup] = useState<SetupData | null>(null)
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null)
  const [step, setStep] = useState<'loading' | 'setup' | 'success' | 'error'>('loading')
  const [serverError, setServerError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const didSetup = useRef(false)

  useEffect(() => {
    if (didSetup.current) return
    didSetup.current = true
    api
      .post<SetupData>('/auth/mfa/setup')
      .then(async (res) => {
        setSetup(res.data)
        const dataUrl = await QRCode.toDataURL(res.data.qr_code_uri)
        setQrDataUrl(dataUrl)
        setStep('setup')
      })
      .catch((err: unknown) => {
        const detail =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Failed to set up MFA. Please try again.'
        setServerError(detail)
        setStep('error')
      })
  }, [attempt])

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  async function onVerify(data: FormData) {
    setServerError(null)
    try {
      await api.post('/auth/mfa/verify', { code: data.code })
      setStep('success')
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Invalid code'
      setServerError(detail)
    }
  }

  const card: React.CSSProperties = {
    background: 'var(--color-card)',
    border: '1px solid var(--color-border)',
    borderRadius: '10px',
    padding: '32px',
    maxWidth: '500px',
  }

  return (
    <div style={{ minHeight: '100svh', background: 'var(--color-bg)' }}>
      <Topbar />
      <div style={{ maxWidth: '900px', margin: '0 auto', padding: '32px 24px' }}>
        <div style={card}>
          {step === 'loading' && (
            <p style={{ color: 'var(--color-text-muted)' }}>Setting up MFA…</p>
          )}

          {step === 'setup' && setup && (
            <>
              <h2 style={{ color: 'var(--color-text)', marginBottom: '20px', fontSize: '18px' }}>
                Set up authenticator
              </h2>
              <p style={{ color: 'var(--color-text-muted)', fontSize: '14px', marginBottom: '16px' }}>
                Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
              </p>
              {qrDataUrl && (
                <img
                  src={qrDataUrl}
                  alt="MFA QR Code"
                  style={{ width: '200px', height: '200px', marginBottom: '16px', borderRadius: '8px' }}
                />
              )}
              <p style={{ color: 'var(--color-text-muted)', fontSize: '13px', marginBottom: '20px' }}>
                Manual key:{' '}
                <code
                  style={{
                    background: 'var(--color-bg)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontFamily: 'monospace',
                    color: 'var(--color-text)',
                  }}
                >
                  {setup.secret}
                </code>
              </p>

              <details style={{ marginBottom: '20px' }}>
                <summary
                  style={{ color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: '14px' }}
                >
                  Show backup codes
                </summary>
                <div
                  style={{
                    background: 'var(--color-bg)',
                    borderRadius: '6px',
                    padding: '12px',
                    marginTop: '8px',
                    fontFamily: 'monospace',
                    fontSize: '13px',
                    color: 'var(--color-text)',
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '4px',
                  }}
                >
                  {setup.backup_codes.map((c) => (
                    <span key={c}>{c}</span>
                  ))}
                </div>
              </details>

              <form onSubmit={handleSubmit(onVerify)} style={styles.form}>
                <FormError message={serverError} />
                <div style={styles.field}>
                  <label style={styles.label}>Verify — enter the code from your app</label>
                  <input {...register('code')} style={styles.input} autoFocus maxLength={6} />
                  {errors.code && <span style={styles.fieldError}>{errors.code.message}</span>}
                </div>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  style={{ ...styles.submitBtn, width: 'auto', padding: '10px 20px' }}
                >
                  {isSubmitting ? 'Verifying…' : 'Enable MFA'}
                </button>
              </form>
            </>
          )}

          {step === 'error' && (
            <>
              <FormError message={serverError} />
              <button
                onClick={() => {
                  didSetup.current = false
                  setServerError(null)
                  setStep('loading')
                  setAttempt((n) => n + 1)
                }}
                style={{ ...styles.submitBtn, width: 'auto', padding: '10px 20px', marginTop: '16px' }}
              >
                Try again
              </button>
            </>
          )}

          {step === 'success' && (
            <>
              <p style={{ color: 'var(--color-success-text)', fontSize: '16px', marginBottom: '16px' }}>
                MFA enabled successfully!
              </p>
              <button
                onClick={() => navigate({ to: '/dashboard' })}
                style={{ ...styles.submitBtn, width: 'auto', padding: '10px 20px' }}
              >
                Back to dashboard
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
