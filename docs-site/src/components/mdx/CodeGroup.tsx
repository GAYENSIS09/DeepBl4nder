'use client'

import { useState } from 'react'

interface CodeGroupProps {
  children: React.ReactNode
}

export function CodeGroup({ children }: CodeGroupProps) {
  return (
    <div className="my-6 rounded-lg border border-db-border overflow-hidden">
      {children}
    </div>
  )
}

interface CodeGroupTabProps {
  label: string
  default?: boolean
  children: React.ReactNode
}

export function CodeGroupTab({ label, children }: CodeGroupTabProps) {
  return (
    <div className="code-group-tab">
      <div className="flex items-center gap-2 px-4 py-2 bg-db-surface border-b border-db-border">
        <span className="text-xs font-medium text-db-muted">{label}</span>
      </div>
      <div className="relative">{children}</div>
    </div>
  )
}
