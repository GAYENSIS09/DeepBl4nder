'use client'

import { useEffect, useState, useRef } from 'react'
import { createPortal } from 'react-dom'
import { X, Search, Command, ArrowRight } from 'lucide-react'
import Link from 'next/link'

interface SearchResult {
  title: string
  description: string
  href: string
  category: string
}

const SEARCH_DATA: SearchResult[] = [
  { title: 'Getting Started', description: 'Installation, configuration, and first run', href: '/docs/getting-started', category: 'Core' },
  { title: 'Architecture', description: 'System overview, project structure, and design principles', href: '/docs/architecture', category: 'Core' },
  { title: 'Agents', description: 'The 14 NOOA agents and their roles', href: '/docs/agents', category: 'Core' },
  { title: 'LLM System', description: 'Local models, cascade routing, and task classification', href: '/docs/llm', category: 'Core' },
  { title: 'Docker', description: 'Container deployment with GPU support', href: '/docs/docker', category: 'Core' },
  { title: 'Development', description: 'Contributing, testing, and code style', href: '/docs/development', category: 'Core' },
  { title: 'Context Management', description: 'RAG, Schema Injection, Pruning, and Caching', href: '/docs/context', category: 'Advanced' },
  { title: 'Diagrams', description: 'PlantUML architecture diagrams', href: '/docs/diagrams', category: 'Advanced' },
]

interface SearchModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const filteredResults = SEARCH_DATA.filter(
    (item) =>
      item.title.toLowerCase().includes(query.toLowerCase()) ||
      item.description.toLowerCase().includes(query.toLowerCase()) ||
      item.category.toLowerCase().includes(query.toLowerCase())
  )

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [isOpen])

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return

      if (e.key === 'Escape') {
        onClose()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((prev) => Math.min(prev + 1, filteredResults.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((prev) => Math.max(prev - 1, 0))
      } else if (e.key === 'Enter' && filteredResults[selectedIndex]) {
        window.location.href = filteredResults[selectedIndex].href
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, filteredResults, selectedIndex, onClose])

  if (!isOpen) return null

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20">,
    document.body
  )
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-2xl mx-4 bg-db-panel border border-db-border rounded-xl shadow-2xl overflow-hidden">
        <div className="p-4 border-b border-db-border flex items-center justify-between">
          <div className="relative w-full max-w-md">
            <label htmlFor="search-input" className="sr-only">Search</label>
            <input
              id="search-input"
              type="search"
              placeholder="Search documentation... (Ctrl+K)"
              className="w-full pl-10 pr-4 py-3 bg-db-bg border border-db-border rounded-lg text-db-text placeholder-db-dim focus:outline-none focus:ring-2 focus:ring-db-accent"
              autoFocus
              autoComplete="off"
              spellCheck={false}
              onChange={(e) => setQuery(e.target.value)}
            />
            <kbd className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] px-2 py-1 bg-db-surface border border-db-border rounded text-db-dim font-mono">
              <kbd className="px-1.5 py-0.5 bg-db-accent/10 text-db-accent rounded">Ctrl</kbd>+<kbd className="px-1.5 py-0.5 bg-db-accent/10 text-db-accent rounded">K</kbd>
            </kbd>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-db-muted hover:text-db-text hover:bg-db-surface/50 rounded-lg transition ml-4 shrink-0"
            aria-label="Close search"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="max-h-96 overflow-y-auto p-4">
          {SEARCH_DATA.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="block px-4 py-3 rounded-lg hover:bg-db-surface/50 transition-colors"
              onClick={() => window.location.href = item.href}
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-db-text">{item.title}</h3>
                  <p className="text-sm text-db-muted">{item.description}</p>
                </div>
                <span className="text-xs text-db-dim bg-db-bg px-2 py-0.5 rounded">{item.category}</span>
              </div>
            </Link>
          ))}
</div>
    </div>
    </div>
    ,
    document.body
  )
}