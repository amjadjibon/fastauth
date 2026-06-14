interface FormErrorProps {
  message: string | null | undefined
}

export function FormError({ message }: FormErrorProps) {
  if (!message) return null
  return (
    <div
      style={{
        background: 'var(--color-error-bg)',
        border: '1px solid var(--color-error-border)',
        color: 'var(--color-error-text)',
        borderRadius: '6px',
        padding: '10px 14px',
        fontSize: '14px',
      }}
    >
      {message}
    </div>
  )
}
