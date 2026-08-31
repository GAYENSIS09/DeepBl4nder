'use client'

import { useState } from 'react'
import { ChevronRight } from 'lucide-react'

interface AccordionItemProps {
  title: string
  children: React.ReactNode
  defaultOpen?: boolean
}

export function AccordionItem({ title, children, defaultOpen = false }: AccordionItemProps) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-db-border rounded-lg my-2 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-4 py-3 text-sm font-medium text-db-text hover:bg-db-surface/50 transition-colors"
      >
        <ChevronRight className={`w-4 h-4 text-db-dim transition-transform ${open ? 'rotate-90' : ''}`} />
        {title}
      </button>
      {open && <div className="px-4 pb-4 text-sm text-db-muted leading-7 border-t border-db-border">{children}</div>}
    </div>
  )
}

interface AccordionProps {
  children: React.ReactNode
}

export function Accordion({ children }: AccordionProps) {
  return <div>{children}</div>
}
