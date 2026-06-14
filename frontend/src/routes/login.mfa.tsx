import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api } from '../lib/api'
import { setTokens } from '../lib/tokens'
import { useAuth } from '../contexts/AuthContext'
import { AuthCard, styles } from '../components/AuthCard'
import { FormError } from '../components/FormError'

const schema = z.object({
  code: z.string().min(1, 'Code is required'),
  is_backup_code: z.boolean(),
})
type FormData = z.infer<typeof schema>

export const Route = createFileRoute('/login/mfa')({
  component: MfaPage,
})

function MfaPage() {
  const navigate = useNavigate()
  const { setUser } = useAuth()
  const [serverError, setServerError] = useState<string | null>(null)
  const state = (history.state ?? {}) as { mfaSessionToken?: string }

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { is_backup_code: false },
  })

  async function onSubmit(data: FormData) {
    setServerError(null)
    try {
      const res = await api.post<{
        access_token: string
        refresh_token: string
      }>('/auth/login/mfa', {
        mfa_session_token: state.mfaSessionToken,
        code: data.code,
        is_backup_code: data.is_backup_code,
      })
      setTokens(res.data.access_token, res.data.refresh_token)
      const me = await api.get('/auth/me')
      setUser(me.data)
      navigate({ to: '/dashboard' })
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Invalid code'
      setServerError(msg)
    }
  }

  return (
    <AuthCard title="Two-factor authentication">
      <form onSubmit={handleSubmit(onSubmit)} style={styles.form}>
        <FormError message={serverError} />
        <div style={styles.field}>
          <label style={styles.label}>Authentication code</label>
          <input
            {...register('code')}
            style={styles.input}
            autoFocus
            placeholder="6-digit code or backup code"
          />
          {errors.code && <span style={styles.fieldError}>{errors.code.message}</span>}
        </div>
        <label style={{ ...styles.label, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input type="checkbox" {...register('is_backup_code')} />
          Use a backup code
        </label>
        <button type="submit" disabled={isSubmitting} style={styles.submitBtn}>
          {isSubmitting ? 'Verifying…' : 'Verify'}
        </button>
      </form>
    </AuthCard>
  )
}
