import { createFileRoute, Link } from '@tanstack/react-router'
import { AuthCard, styles } from '../components/AuthCard'

export const Route = createFileRoute('/register/success')({
  component: RegisterSuccessPage,
})

function RegisterSuccessPage() {
  return (
    <AuthCard title="Check your email">
      <p
        style={{
          color: 'var(--color-text-muted)',
          fontSize: '15px',
          lineHeight: '1.6',
          textAlign: 'center',
        }}
      >
        We sent a verification link to your email address. Click the link to activate your account.
      </p>
      <div style={{ ...styles.footer, marginTop: '28px' }}>
        <Link to="/login" style={styles.link}>
          Back to sign in
        </Link>
      </div>
    </AuthCard>
  )
}
