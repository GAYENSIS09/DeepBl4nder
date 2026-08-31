'use client'

import { useState } from 'react'

interface StepProps {
  number: number
  title: string
  children: React.ReactNode
}

export function Step({ number, title, children }: StepProps) {
  return (
    <div className="flex gap-4 my-6">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-db-accent/10 border border-db-accent/30 flex items-center justify-center">
        <span className="text-sm font-bold text-db-accent">{number}</span>
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="font-semibold text-db-text mb-2">{title}</h4>
        <div className="text-sm text-db-muted leading-7">{children}</div>
      </div>
    </div>
  )
}

interface StepsProps {
  children: React.ReactNode
}

export function Steps({ children }: StepsProps) {
  return <div className="relative pl-4 border-l border-db-border">{children}</div>
}
