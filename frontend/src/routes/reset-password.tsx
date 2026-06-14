import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api } from '../lib/api'
import { AuthCard, styles } from '../components/AuthCard'
import { FormError } from '../components/FormError'

const schema = z.object({
  new_password: z
    .string()
    .min(8, 'Must be at least 8 characters')
    .regex(/[A-Z]/, 'Must contain at least one uppercase letter')
    .regex(/[0-9]/, 'Must contain at least one number'),
})
type FormData = z.infer<typeof schema>

export const Route = createFileRoute('/reset-password')({
  validateSearch: (s: Record<string, unknown>) => ({ token: (s.token as string) ?? '' }),
  component: ResetPasswordPage,
})

function ResetPasswordPage() {
  const { token } = Route.useSearch()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  async function onSubmit(data: FormData) {
    setServerError(null)
    try {
      await api.post('/auth/reset-password', { token, new_password: data.new_password })
      navigate({ to: '/login', search: { reset: 'success' } } as never)
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Reset failed. The link may have expired.'
      setServerError(detail)
    }
  }

  if (!token) {
    return (
      <AuthCard title="Invalid link">
        <p style={{ color: 'var(--color-error-text)', textAlign: 'center' }}>
          No reset token provided.
        </p>
        <div style={{ ...styles.footer, marginTop: '16px' }}>
          <Link to="/forgot-password" style={styles.link}>
            Request a new link
          </Link>
        </div>
      </AuthCard>
    )
  }

  return (
    <AuthCard title="Set new password">
      <form onSubmit={handleSubmit(onSubmit)} style={styles.form}>
        <FormError message={serverError} />
        <div style={styles.field}>
          <label style={styles.label}>New password</label>
          <input
            {...register('new_password')}
            type="password"
            style={styles.input}
            autoFocus
            autoComplete="new-password"
          />
          {errors.new_password && (
            <span style={styles.fieldError}>{errors.new_password.message}</span>
          )}
        </div>
        <button type="submit" disabled={isSubmitting} style={styles.submitBtn}>
          {isSubmitting ? 'Saving…' : 'Set new password'}
        </button>
      </form>
    </AuthCard>
  )
}
