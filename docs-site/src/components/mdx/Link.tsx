import { ExternalLink } from 'lucide-react'

interface LinkProps {
  href: string
  children: React.ReactNode
  external?: boolean
}

export function Link({ href, children, external }: LinkProps) {
  const isExternal = external || href.startsWith('http')
  return (
    <a
      href={href}
      className="inline-flex items-center gap-1 text-db-accent hover:text-db-accent2 transition-colors"
      {...(isExternal ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
    >
      {children}
      {isExternal && <ExternalLink className="w-3 h-3" />}
    </a>
  )
}
