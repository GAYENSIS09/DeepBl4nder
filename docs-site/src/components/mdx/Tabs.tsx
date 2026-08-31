'use client'

import { useState } from 'react'

interface TabsProps {
  children: React.ReactNode
  defaultValue?: string
}

interface TabItemProps {
  value: string
  label: string
  children: React.ReactNode
}

export function Tabs({ children, defaultValue }: TabsProps) {
  const [active, setActive] = useState(defaultValue || '')
  const tabs = Array.isArray(children) ? children : [children]
  const items = tabs.filter((t: any) => t?.props?.value)

  const activeItem = items.find((t: any) => t.props.value === active) || items[0]

  return (
    <div className="my-6">
      <div className="flex gap-1 border-b border-db-border mb-4">
        {items.map((item: any) => (
          <button
            key={item.props.value}
            onClick={() => setActive(item.props.value)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              active === item.props.value
                ? 'text-db-accent border-db-accent'
                : 'text-db-muted border-transparent hover:text-db-text'
            }`}
          >
            {item.props.label}
          </button>
        ))}
      </div>
      <div>{activeItem}</div>
    </div>
  )
}

export function TabItem({ children }: TabItemProps) {
  return <div>{children}</div>
}
