import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api } from '../lib/api'
import { AuthCard, styles } from '../components/AuthCard'
import { FormError } from '../components/FormError'

const schema = z.object({
  username: z
    .string()
    .min(3, 'Must be at least 3 characters')
    .max(32, 'Must be 32 characters or fewer')
    .regex(/^[a-zA-Z0-9_-]+$/, 'Only letters, numbers, hyphens and underscores'),
  email: z.string().email('Enter a valid email address'),
  password: z
    .string()
    .min(8, 'Must be at least 8 characters')
    .regex(/[A-Z]/, 'Must contain at least one uppercase letter')
    .regex(/[0-9]/, 'Must contain at least one number'),
})
type FormData = z.infer<typeof schema>

export const Route = createFileRoute('/register')({
  component: RegisterPage,
})

function RegisterPage() {
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
      await api.post('/auth/register', data)
      navigate({ to: '/register/success' })
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      const msg = Array.isArray(detail)
        ? detail.map((d: { msg?: string }) => d.msg).join(', ')
        : typeof detail === 'string'
          ? detail
          : 'Registration failed'
      setServerError(msg)
    }
  }

  return (
    <AuthCard title="Create your account">
      <form onSubmit={handleSubmit(onSubmit)} style={styles.form}>
        <FormError message={serverError} />
        <div style={styles.field}>
          <label style={styles.label}>Username</label>
          <input {...register('username')} style={styles.input} autoFocus autoComplete="username" />
          {errors.username && <span style={styles.fieldError}>{errors.username.message}</span>}
        </div>
        <div style={styles.field}>
          <label style={styles.label}>Email</label>
          <input {...register('email')} type="email" style={styles.input} autoComplete="email" />
          {errors.email && <span style={styles.fieldError}>{errors.email.message}</span>}
        </div>
        <div style={styles.field}>
          <label style={styles.label}>Password</label>
          <input
            {...register('password')}
            type="password"
            style={styles.input}
            autoComplete="new-password"
          />
          {errors.password && <span style={styles.fieldError}>{errors.password.message}</span>}
        </div>
        <button type="submit" disabled={isSubmitting} style={styles.submitBtn}>
          {isSubmitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <div style={styles.footer}>
        Already have an account?{' '}
        <Link to="/login" style={styles.link}>
          Sign in
        </Link>
      </div>
    </AuthCard>
  )
}
