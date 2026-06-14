import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { AuthCard, styles } from '../components/AuthCard'
import { FormError } from '../components/FormError'
import { useAuth } from '../contexts/AuthContext'

const schema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
})
type FormData = z.infer<typeof schema>

export const Route = createFileRoute('/login')({
  component: LoginPage,
})

function LoginPage() {
  const { login } = useAuth()
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
      const result = await login(data.username, data.password)
      if (result.mfa_required) {
        navigate({
          to: '/login/mfa',
          state: { mfaSessionToken: result.mfa_session_token },
        } as never)
      } else {
        navigate({ to: '/dashboard' })
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Invalid credentials'
      setServerError(msg)
    }
  }

  return (
    <AuthCard title="Sign in to FastAuth">
      <form onSubmit={handleSubmit(onSubmit)} style={styles.form}>
        <FormError message={serverError} />
        <div style={styles.field}>
          <label style={styles.label}>Username</label>
          <input {...register('username')} style={styles.input} autoFocus autoComplete="username" />
          {errors.username && <span style={styles.fieldError}>{errors.username.message}</span>}
        </div>
        <div style={styles.field}>
          <label style={styles.label}>Password</label>
          <input
            {...register('password')}
            type="password"
            style={styles.input}
            autoComplete="current-password"
          />
          {errors.password && <span style={styles.fieldError}>{errors.password.message}</span>}
        </div>
        <button type="submit" disabled={isSubmitting} style={styles.submitBtn}>
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
      <div style={styles.footer}>
        <Link to="/forgot-password" style={styles.link}>
          Forgot password?
        </Link>
        {' · '}
        <Link to="/register" style={styles.link}>
          Create account
        </Link>
      </div>
    </AuthCard>
  )
}
