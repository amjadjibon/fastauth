import { createFileRoute, Link } from '@tanstack/react-router'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api } from '../lib/api'
import { AuthCard, styles } from '../components/AuthCard'
import { FormError } from '../components/FormError'

const schema = z.object({
  email: z.string().email('Enter a valid email address'),
})
type FormData = z.infer<typeof schema>

export const Route = createFileRoute('/forgot-password')({
  component: ForgotPasswordPage,
})

function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  async function onSubmit(data: FormData) {
    setServerError(null)
    try {
      await api.post('/auth/forgot-password', data)
    } catch {
      // intentionally swallowed — always show neutral message
    }
    setSubmitted(true)
  }

  if (submitted) {
    return (
      <AuthCard title="Check your email">
        <p
          style={{ color: 'var(--color-text-muted)', fontSize: '15px', textAlign: 'center', lineHeight: '1.6' }}
        >
          If that email address is registered, we've sent a password reset link. Check your inbox.
        </p>
        <div style={{ ...styles.footer, marginTop: '20px' }}>
          <Link to="/login" style={styles.link}>
            Back to sign in
          </Link>
        </div>
      </AuthCard>
    )
  }

  return (
    <AuthCard title="Reset your password">
      <form onSubmit={handleSubmit(onSubmit)} style={styles.form}>
        <FormError message={serverError} />
        <div style={styles.field}>
          <label style={styles.label}>Email address</label>
          <input {...register('email')} type="email" style={styles.input} autoFocus />
          {errors.email && <span style={styles.fieldError}>{errors.email.message}</span>}
        </div>
        <button type="submit" disabled={isSubmitting} style={styles.submitBtn}>
          {isSubmitting ? 'Sending…' : 'Send reset link'}
        </button>
      </form>
      <div style={styles.footer}>
        <Link to="/login" style={styles.link}>
          Back to sign in
        </Link>
      </div>
    </AuthCard>
  )
}
