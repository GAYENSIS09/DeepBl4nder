import Link from 'next/link'
import { ArrowRight } from 'lucide-react'

const DOCS = [
  { href: '/docs/getting-started', title: 'Getting Started', desc: 'Installation, configuration, and first run.', num: '01' },
  { href: '/docs/architecture', title: 'Architecture', desc: 'System overview, project structure, and design principles.', num: '02' },
  { href: '/docs/agents', title: 'Agents', desc: 'The 14 NOOA agents and their roles.', num: '03' },
  { href: '/docs/llm', title: 'LLM System', desc: 'Local models, cascade routing, and task classification.', num: '04' },
  { href: '/docs/docker', title: 'Docker', desc: 'Container deployment with GPU support.', num: '05' },
  { href: '/docs/development', title: 'Development', desc: 'Contributing, testing, and code style.', num: '06' },
  { href: '/docs/context', title: 'Context Management', desc: 'RAG, Schema Injection, Pruning, and Caching.', num: '07' },
  { href: '/docs/diagrams', title: 'Diagrams', desc: 'PlantUML architecture diagrams.', num: '08' },
]

export default function DocsIndex() {
  return (
    <div>
      <h1 className="text-4xl font-bold text-db-text mb-3">Documentation</h1>
      <p className="text-db-muted mb-10 text-lg">Everything you need to use and extend DeepBl4nder.</p>

      <div className="space-y-4">
        {DOCS.map(({ href, title, desc, num }) => (
          <Link key={href} href={href} className="group block bg-db-surface border border-db-border rounded-xl p-6 hover:border-db-accent/30 transition-all hover:glow-sm">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-4">
                <span className="text-db-accent font-mono text-sm mt-0.5">{num}</span>
                <div>
                  <h3 className="font-semibold text-db-text group-hover:text-db-accent transition text-lg">{title}</h3>
                  <p className="text-sm text-db-muted mt-1">{desc}</p>
                </div>
              </div>
              <ArrowRight className="w-5 h-5 text-db-dim group-hover:text-db-accent transition mt-1 shrink-0" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}



