import { Quote as QuoteIcon } from 'lucide-react'

interface QuoteProps {
  children: React.ReactNode
  author?: string
}

export function Quote({ children, author }: QuoteProps) {
  return (
    <div className="my-6 p-6 rounded-lg bg-db-surface/50 border border-db-border relative">
      <QuoteIcon className="absolute top-4 left-4 w-6 h-6 text-db-accent/20" />
      <div className="pl-8 text-db-muted italic leading-7">{children}</div>
      {author && (
        <div className="pl-8 mt-3 text-sm text-db-dim">— {author}</div>
      )}
    </div>
  )
}
