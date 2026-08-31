import Link from 'next/link'
import { BookOpen, Layers, Bot, Workflow, Brain, Database, Network, Puzzle, Cpu, FileCode, Box, Container, Terminal, GitPullRequest } from 'lucide-react'

export const metadata = {
  title: 'Documentation - DeepBl4nder',
  description: 'Complete documentation for the DeepBl4nder AI production pipeline.',
}

const sections = [
  { href: '/docs/getting-started', title: 'Getting Started', description: 'Installation, prerequisites, and quickstart guide', icon: BookOpen, color: '#AAFF00' },
  { href: '/docs/architecture', title: 'Architecture', description: 'System overview, 4-layer design, and principles', icon: Layers, color: '#AAFF00' },
  { href: '/docs/agents', title: 'Agents (14)', description: 'All NOOA agents with roles, inputs/outputs, and skills', icon: Bot, color: '#88CC00' },
  { href: '/docs/pipeline', title: 'Production Pipeline', description: 'Pipeline runner, checkpoints, revision loop, budget', icon: Workflow, color: '#56B6C2' },
  { href: '/docs/llm-system', title: 'LLM System', description: 'TaskClassifier, CascadeRouter, 3 Qwen3 local models', icon: Brain, color: '#E6C229' },
  { href: '/docs/context', title: 'Context Management', description: 'ContextInjector, Pruner, PromptCache, NOOA native', icon: Database, color: '#56B6C2' },
  { href: '/docs/knowledge-graph', title: 'Knowledge Graph', description: 'KnowledgeGraphPlugin, SchemaVectorStore, TF-IDF', icon: Network, color: '#AAFF00' },
  { href: '/docs/skills', title: 'Skills (36+)', description: 'Progressive disclosure, SKILL.md format, skill loading', icon: Puzzle, color: '#88CC00' },
  { href: '/docs/bridges', title: 'Bridges & Engines', description: 'Blender, UE5, Godot, AI Video engine integration', icon: Cpu, color: '#E6C229' },
  { href: '/docs/codegen', title: 'CodeGen', description: 'AST validator, CodePolicy, script validation', icon: FileCode, color: '#56B6C2' },
  { href: '/docs/plugins', title: 'Plugins', description: '10 built-in plugins: rendering, audio, storage, git', icon: Box, color: '#FF5C57' },
  { href: '/docs/docker', title: 'Docker Setup', description: 'Services, profiles, GPU config, dockerfiles', icon: Container, color: '#56B6C2' },
  { href: '/docs/tui', title: 'TUI Interface', description: 'Textual terminal UI, EmbeddedAPI, EventBridge', icon: Terminal, color: '#AAFF00' },
  { href: '/docs/cli', title: 'CLI Reference', description: 'All CLI commands and options', icon: Terminal, color: '#7A7A72' },
  { href: '/docs/contributing', title: 'Contributing', description: 'Guide for contributors, architecture for contributors', icon: GitPullRequest, color: '#88CC00' },
]

export default function DocsPage() {
  return (
    <>
      <h1 className="text-4xl font-bold text-db-text mb-2">Documentation</h1>
      <p className="text-db-muted text-lg mb-10">
        Complete documentation for DeepBl4nder — an open-source, local-first AI production pipeline
        that transforms text prompts into 3D scenes using 14 specialized agents.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sections.map((section) => {
          const Icon = section.icon
          return (
            <Link
              key={section.href}
              href={section.href}
              className="group block rounded-lg border border-db-border bg-db-surface p-5 transition-all hover:border-db-accent/30 hover:bg-db-surface/80 no-underline"
            >
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-db-bg border border-db-border group-hover:border-db-accent/30 transition-colors">
                  <Icon className="w-5 h-5" style={{ color: section.color }} />
                </div>
                <div>
                  <h3 className="font-semibold text-db-text group-hover:text-db-accent transition-colors text-sm">
                    {section.title}
                  </h3>
                  <p className="text-xs text-db-dim mt-1 leading-relaxed">{section.description}</p>
                </div>
              </div>
            </Link>
          )
        })}
      </div>
    </>
  )
}
