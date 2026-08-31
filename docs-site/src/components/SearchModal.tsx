'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Search, X, FileText, ArrowRight } from 'lucide-react'

const SEARCH_DATA = [
  { title: 'Getting Started', description: 'Installation, prerequisites, and quickstart guide', href: '/docs/getting-started', category: 'Core' },
  { title: 'Architecture', description: 'System overview, layers, and design principles', href: '/docs/architecture', category: 'Core' },
  { title: 'Agents (14)', description: 'All 14 NOOA agents with roles, inputs/outputs, and skills', href: '/docs/agents', category: 'Core' },
  { title: 'Production Pipeline', description: 'Pipeline runner, checkpoints, revision loop, budget', href: '/docs/pipeline', category: 'Core' },
  { title: 'LLM System', description: 'TaskClassifier, CascadeRouter, model server, 3 Qwen3 models', href: '/docs/llm-system', category: 'Core' },
  { title: 'Context Management', description: 'ContextInjector, ContextPruner, PromptCacheManager', href: '/docs/context', category: 'Advanced' },
  { title: 'Knowledge Graph', description: 'KnowledgeGraphPlugin, SchemaVectorStore, TF-IDF search', href: '/docs/knowledge-graph', category: 'Advanced' },
  { title: 'Skills System', description: '36+ embedded skills with progressive disclosure', href: '/docs/skills', category: 'Advanced' },
  { title: 'Bridges & Engines', description: 'Blender, UE5, Godot, AI Video engine bridges', href: '/docs/bridges', category: 'Advanced' },
  { title: 'CodeGen', description: 'AST validator, CodePolicy, script validation', href: '/docs/codegen', category: 'Advanced' },
  { title: 'Plugins', description: '10 built-in plugins for rendering, audio, storage', href: '/docs/plugins', category: 'Advanced' },
  { title: 'Docker Setup', description: 'Services, profiles, GPU configuration, dockerfiles', href: '/docs/docker', category: 'Ops' },
  { title: 'TUI Interface', description: 'Textual terminal UI, EmbeddedAPI, EventBridge', href: '/docs/tui', category: 'Ops' },
  { title: 'CLI Reference', description: 'All CLI commands and options', href: '/docs/cli', category: 'Ops' },
  { title: 'Contributing', description: 'Guide for contributors, architecture for contributors', href: '/docs/contributing', category: 'Community' },
]

interface SearchModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const router = useRouter()
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const filtered = query.trim()
    ? SEARCH_DATA.filter(
        (item) =>
          item.title.toLowerCase().includes(query.toLowerCase()) ||
          item.description.toLowerCase().includes(query.toLowerCase()) ||
          item.category.toLowerCase().includes(query.toLowerCase())
      )
    : SEARCH_DATA

  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  const navigate = useCallback(
    (href: string) => {
      onClose()
      router.push(href)
    },
    [onClose, router]
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((i) => Math.max(i - 1, 0))
      } else if (e.key === 'Enter' && filtered[selectedIndex]) {
        navigate(filtered[selectedIndex].href)
      }
    },
    [filtered, selectedIndex, navigate]
  )

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]">
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-xl bg-db-panel border border-db-border rounded-xl shadow-2xl overflow-hidden">
        <div className="flex items-center gap-3 px-4 border-b border-db-border">
          <Search className="w-5 h-5 text-db-dim" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search documentation..."
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0) }}
            onKeyDown={handleKeyDown}
            className="flex-1 py-4 bg-transparent text-db-text placeholder-db-dim outline-none text-sm"
          />
          <button onClick={onClose} className="p-1 text-db-dim hover:text-db-text">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="max-h-[50vh] overflow-y-auto p-2">
          {filtered.length === 0 ? (
            <div className="py-8 text-center text-db-dim text-sm">No results found</div>
          ) : (
            filtered.map((item, i) => (
              <button
                key={item.href}
                onClick={() => navigate(item.href)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                  i === selectedIndex ? 'bg-db-accent/10 text-db-accent' : 'text-db-muted hover:bg-db-surface/50'
                }`}
              >
                <FileText className="w-4 h-4 flex-shrink-0 opacity-50" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{item.title}</div>
                  <div className="text-xs text-db-dim truncate">{item.description}</div>
                </div>
                <span className="text-[10px] uppercase tracking-wider text-db-dim bg-db-surface px-1.5 py-0.5 rounded flex-shrink-0">
                  {item.category}
                </span>
                <ArrowRight className="w-3 h-3 opacity-0 group-hover:opacity-100" />
              </button>
            ))
          )}
        </div>
        <div className="flex items-center gap-4 px-4 py-2 border-t border-db-border text-[10px] text-db-dim">
          <span><kbd className="px-1 py-0.5 bg-db-surface border border-db-border rounded">↑↓</kbd> navigate</span>
          <span><kbd className="px-1 py-0.5 bg-db-surface border border-db-border rounded">↵</kbd> select</span>
          <span><kbd className="px-1 py-0.5 bg-db-surface border border-db-border rounded">esc</kbd> close</span>
        </div>
      </div>
    </div>
  )
}
