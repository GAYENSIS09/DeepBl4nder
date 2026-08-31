interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'accent' | 'info' | 'warning' | 'success' | 'danger'
  size?: 'sm' | 'md'
}

const VARIANT_STYLES: Record<string, string> = {
  default: 'bg-db-surface text-db-muted border-db-border',
  accent: 'bg-db-accent/10 text-db-accent border-db-accent/30',
  info: 'bg-db-info/10 text-db-info border-db-info/30',
  warning: 'bg-db-warn/10 text-db-warn border-db-warn/30',
  success: 'bg-db-accent/10 text-db-accent border-db-accent/30',
  danger: 'bg-db-error/10 text-db-error border-db-error/30',
}

export function Badge({ children, variant = 'default', size = 'sm' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center border rounded-full font-medium
      ${VARIANT_STYLES[variant]}
      ${size === 'sm' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-0.5'}
    `}>
      {children}
    </span>
  )
}
