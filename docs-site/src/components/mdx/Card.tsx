import { ArrowRight } from 'lucide-react'

interface CardProps {
  title: string
  description?: string
  href?: string
  icon?: React.ReactNode
  badge?: string
  children?: React.ReactNode
  className?: string
}

export function Card({ title, description, href, icon, badge, children, className = '' }: CardProps) {
  const content = (
    <div className={`group relative rounded-lg border border-db-border bg-db-surface p-6 transition-all hover:border-db-accent/30 hover:bg-db-surface/80 ${className}`}>
      {badge && (
        <span className="inline-block text-[10px] uppercase tracking-wider font-semibold text-db-accent bg-db-accent/10 px-2 py-0.5 rounded-full mb-3">
          {badge}
        </span>
      )}
      <div className="flex items-start gap-3">
        {icon && <div className="text-db-accent mt-0.5">{icon}</div>}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-db-text group-hover:text-db-accent transition-colors">{title}</h3>
          {description && <p className="text-sm text-db-muted mt-1">{description}</p>}
          {children}
        </div>
      </div>
      {href && (
        <div className="absolute right-4 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
          <ArrowRight className="w-4 h-4 text-db-accent" />
        </div>
      )}
    </div>
  )

  if (href) {
    return <a href={href} className="block no-underline">{content}</a>
  }
  return content
}

interface CardGridProps {
  children: React.ReactNode
  cols?: 2 | 3 | 4
}

export function CardGrid({ children, cols = 3 }: CardGridProps) {
  const gridClass = {
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
  }[cols]

  return (
    <div className={`grid ${gridClass} gap-4 my-6`}>
      {children}
    </div>
  )
}
