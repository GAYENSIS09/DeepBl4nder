'use client'

import Link from 'next/link'
import { Search, Menu, X, Github, BookOpen, Terminal, Cpu, Box as BoxIcon, Settings } from 'lucide-react'
import { useState, useEffect } from 'react'
import SearchModal from './SearchModal'

const NAV = [
  { href: '/docs/getting-started', label: 'Getting Started', icon: '📖', group: 'Core' },
  { href: '/docs/architecture', label: 'Architecture', icon: '🏗️', group: 'Core' },
  { href: '/docs/agents', label: 'Agents', icon: '🤖', group: 'Core' },
  { href: '/docs/llm', label: 'LLM System', icon: '🧠', group: 'Core' },
  { href: '/docs/docker', label: 'Docker', icon: '🐳', group: 'Core' },
  { href: '/docs/development', label: 'Development', icon: '⚙️', group: 'Core' },
  { href: '/docs/context', label: 'Context Management', icon: '📚', group: 'Advanced' },
  { href: '/docs/diagrams', label: 'Diagrams', icon: '📊', group: 'Advanced' },
]

export default function Sidebar({ current }: { current?: string }) {
  const [searchQuery, setSearchQuery] = useState('')
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isSearchOpen, setIsSearchOpen] = useState(false)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setIsSearchOpen(true)
      }
      if (e.key === 'Escape') {
        setIsSearchOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <>
      {/* Mobile menu button */}
      <button
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-db-surface border border-db-border rounded-lg text-db-text"
        onClick={() => setIsMobileMenuOpen(true)}
        aria-label="Open menu"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Mobile overlay */}
      {isMobileMenuOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40 bg-black/50"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`w-64 shrink-0 border-r border-db-border bg-db-panel min-h-screen p-5 transition-transform duration-300 lg:translate-x-0 ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'} fixed lg:static inset-y-0 left-0 z-50`}
      >
        <div className="flex items-center justify-between mb-10">
          <a href="/" className="flex items-center gap-2">
            <img src="/DeepBl4nder/logo.svg" alt="DeepBl4nder" width={130} height={32} />
          </a>
          <button
            className="lg:hidden p-1 text-db-muted hover:text-db-text"
            onClick={() => setIsMobileMenuOpen(false)}
            aria-label="Close menu"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Search trigger */}
        <button
          onClick={() => setIsSearchOpen(true)}
          className="w-full relative mb-6"
        >
          <div className="relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-db-dim" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="search"
              placeholder="Search docs... (Ctrl+K)"
              readOnly
              onClick={() => setIsSearchOpen(true)}
              className="w-full pl-9 pr-3 py-2 bg-db-surface border border-db-border rounded-lg text-sm text-db-text placeholder-db-dim"
            />
            <kbd className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] px-1.5 py-0.5 bg-db-surface border border-db-border rounded text-db-dim font-mono">
              Ctrl+K
            </kbd>
          </div>
        </button>

        <nav className="space-y-1">
          <p className="text-[10px] uppercase tracking-widest text-db-dim font-semibold mb-3 px-3">
            Core Documentation
          </p>
          {NAV.filter(n => n.group === 'Core').map(({ href, label, icon }) => {
            const active = current === href.split('/').pop()
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                  active
                    ? 'bg-db-accent/10 text-db-accent border-l-2 border-db-accent font-medium'
                    : 'text-db-muted hover:text-db-text hover:bg-db-surface/50'
                }`}
              >
                <span className="text-lg">{icon}</span>
                {label}
              </Link>
            )
          })}
        </nav>

        <nav className="mt-8 space-y-1">
          <p className="text-[10px] uppercase tracking-widest text-db-dim font-semibold mb-3 px-3">
            Advanced
          </p>
          {NAV.filter(n => n.group === 'Advanced').map(({ href, label, icon }) => {
            const active = current === href.split('/').pop()
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                  active
                    ? 'bg-db-accent/10 text-db-accent border-l-2 border-db-accent font-medium'
                    : 'text-db-muted hover:text-db-text hover:bg-db-surface/50'
                }`}
              >
                <span className="text-lg">{icon}</span>
                {label}
              </Link>
            )
          })}
        </nav>

        <div className="mt-10 pt-6 border-t border-db-border">
          <p className="text-[10px] uppercase tracking-widest text-db-dim font-semibold mb-3 px-3">
            Resources
          </p>
          <a
            href="https://github.com/GAYENSIS09/DeepBl4nder"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 px-3 py-2 text-sm text-db-muted hover:text-db-text hover:bg-db-surface/50 rounded-lg transition"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0c-6.626 0-12 4.874-12 10.874 0 4.412 2.865 8.167 6.836 9.486.5.09.683-.216.683-.482 0-.238-.009-.866-.013-1.7-2.78.604-3.376-1.34-3.376-1.34-.457-1.155-1.114-1.46-1.114-1.46-.91-.621.07-.608.07-.608 1.004.07 1.531 1.03 1.531 1.03.892 1.528 2.34 1.086 2.91.832.09-.65.35-1.097.634-1.344-2.22-.253-4.55-1.11-4.55-4.94 0-1.092.39-1.984 1.03-2.684-.103-.252-.448-1.27.1-2.646 0 0 .84-.268 2.75 1.024.79-.22 1.64-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.024 2.75 1.024.546 1.376.205 2.658.097 2.646.637.7 1.03 1.592 1.03 2.684 0 3.85-2.34 4.78-4.56 4.93.36.3.678 2.102.678 4.25 0 1.51-.012 2.722-.012 3.09 0 .268.18.579.684.48C20.886 19.998 24 15.56 24 10.875 24 4.874 18.627 0 12 0z"/>
            </svg>
            GitHub
          </a>
          <a
            href="https://github.com/GAYENSIS09/DeepBl4nder/issues"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 px-3 py-2 text-sm text-db-muted hover:text-db-text hover:bg-db-surface/50 rounded-lg transition"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Report Issue
          </a>
        </div>
      </aside>
    </>
  )
}
