import Link from 'next/link'
import Image from 'next/image'
import { Box } from 'lucide-react'

const NAV = [
  { href: '/docs/getting-started', label: 'Getting Started', icon: '01' },
  { href: '/docs/architecture', label: 'Architecture', icon: '02' },
  { href: '/docs/agents', label: 'Agents', icon: '03' },
  { href: '/docs/llm', label: 'LLM System', icon: '04' },
  { href: '/docs/docker', label: 'Docker', icon: '05' },
  { href: '/docs/development', label: 'Development', icon: '06' },
]

export default function Sidebar({ current }: { current?: string }) {
  return (
    <aside className="w-64 shrink-0 border-r border-db-border bg-db-panel/50 min-h-screen p-5">
      <Link href="/" className="flex items-center gap-2 mb-10">
        <Image src="/logo.svg" alt="DeepBl4nder" width={130} height={32} priority />
      </Link>

      <nav className="space-y-1">
        <p className="text-[10px] uppercase tracking-widest text-db-dim font-semibold mb-3 px-3">
          Documentation
        </p>
        {NAV.map(({ href, label, icon }) => {
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
              <span className={`text-[10px] font-mono ${active ? 'text-db-accent' : 'text-db-dim'}`}>
                {icon}
              </span>
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
          <span className="text-[10px] font-mono text-db-dim">GH</span>
          GitHub
        </a>
        <a
          href="https://github.com/GAYENSIS09/DeepBl4nder/issues"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-3 px-3 py-2 text-sm text-db-muted hover:text-db-text hover:bg-db-surface/50 rounded-lg transition"
        >
          <span className="text-[10px] font-mono text-db-dim">??</span>
          Report Issue
        </a>
      </div>
    </aside>
  )
}
