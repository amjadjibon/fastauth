import type { CSSProperties, ReactNode } from 'react'

export const styles = {
  overlay: {
    minHeight: '100svh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--color-bg)',
    padding: '24px',
  } as CSSProperties,
  card: {
    background: 'var(--color-card)',
    border: '1px solid var(--color-border)',
    borderRadius: '12px',
    padding: '40px',
    width: '100%',
    maxWidth: '420px',
  } as CSSProperties,
  title: {
    color: 'var(--color-text)',
    fontSize: '22px',
    fontWeight: 600,
    marginBottom: '24px',
    textAlign: 'center',
  } as CSSProperties,
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  } as CSSProperties,
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  } as CSSProperties,
  label: {
    color: 'var(--color-text-muted)',
    fontSize: '13px',
    fontWeight: 500,
  } as CSSProperties,
  input: {
    background: 'var(--color-bg)',
    border: '1px solid var(--color-border)',
    borderRadius: '6px',
    color: 'var(--color-text)',
    fontSize: '15px',
    padding: '10px 12px',
    outline: 'none',
    width: '100%',
    boxSizing: 'border-box',
  } as CSSProperties,
  submitBtn: {
    background: 'var(--color-accent)',
    border: 'none',
    borderRadius: '6px',
    color: '#fff',
    cursor: 'pointer',
    fontSize: '15px',
    fontWeight: 600,
    padding: '12px',
    width: '100%',
    marginTop: '8px',
  } as CSSProperties,
  link: {
    color: 'var(--color-accent)',
    textDecoration: 'none',
    fontSize: '14px',
  } as CSSProperties,
  footer: {
    textAlign: 'center',
    color: 'var(--color-text-muted)',
    fontSize: '14px',
    marginTop: '20px',
  } as CSSProperties,
  fieldError: {
    color: 'var(--color-error-text)',
    fontSize: '12px',
  } as CSSProperties,
}

export function AuthCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div style={styles.overlay}>
      <div style={styles.card}>
        <h1 style={styles.title}>{title}</h1>
        {children}
      </div>
    </div>
  )
}
