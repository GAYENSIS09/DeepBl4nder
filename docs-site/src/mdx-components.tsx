import type { MDXComponents } from 'mdx/types'
import { Callout } from '@/components/mdx/Callout'
import { CodeGroup, CodeGroupTab } from '@/components/mdx/CodeGroup'
import { Card, CardGrid } from '@/components/mdx/Card'
import { Badge } from '@/components/mdx/Badge'
import { Step, Steps } from '@/components/mdx/Steps'
import { MermaidDiagram } from '@/components/diagrams/MermaidDiagram'
import { Tabs, TabItem } from '@/components/mdx/Tabs'
import { FileTree, FileTreeItem } from '@/components/mdx/FileTree'
import { Accordion, AccordionItem } from '@/components/mdx/Accordion'
import { Quote } from '@/components/mdx/Quote'
import { Kbd } from '@/components/mdx/Kbd'
import { Link } from '@/components/mdx/Link'

export function useMDXComponents(components: MDXComponents): MDXComponents {
  return {
    Callout,
    CodeGroup,
    CodeGroupTab,
    Card,
    CardGrid,
    Badge,
    Step,
    Steps,
    MermaidDiagram,
    Tabs,
    TabItem,
    FileTree,
    FileTreeItem,
    Accordion,
    AccordionItem,
    Quote,
    Kbd,
    Link,
    h1: ({ children }) => (
      <h1 className="text-4xl font-bold text-db-text mt-12 mb-4 tracking-tight">{children}</h1>
    ),
    h2: ({ children, ...props }) => (
      <h2 className="text-2xl font-bold text-db-text mt-10 mb-4 pb-2 border-b border-db-border" {...props}>{children}</h2>
    ),
    h3: ({ children, ...props }) => (
      <h3 className="text-xl font-semibold text-db-text mt-8 mb-3" {...props}>{children}</h3>
    ),
    h4: ({ children }) => (
      <h4 className="text-lg font-semibold text-db-text mt-6 mb-2">{children}</h4>
    ),
    p: ({ children }) => (
      <p className="text-db-muted leading-7 mb-4">{children}</p>
    ),
    ul: ({ children }) => (
      <ul className="list-disc list-inside text-db-muted mb-4 space-y-1 ml-2">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal list-inside text-db-muted mb-4 space-y-1 ml-2">{children}</ol>
    ),
    li: ({ children }) => (
      <li className="leading-7">{children}</li>
    ),
    blockquote: ({ children }) => (
      <blockquote className="border-l-4 border-db-accent pl-4 my-4 text-db-muted italic">{children}</blockquote>
    ),
    hr: () => <hr className="my-8 border-db-border" />,
    table: ({ children }) => (
      <div className="overflow-x-auto my-6">
        <table className="w-full text-sm text-left">{children}</table>
      </div>
    ),
    thead: ({ children }) => (
      <thead className="text-xs uppercase text-db-dim bg-db-surface border-b border-db-border">{children}</thead>
    ),
    tbody: ({ children }) => (
      <tbody className="divide-y divide-db-border">{children}</tbody>
    ),
    tr: ({ children }) => (
      <tr className="border-b border-db-border hover:bg-db-surface/50">{children}</tr>
    ),
    th: ({ children }) => (
      <th className="px-4 py-3 font-medium text-db-text">{children}</th>
    ),
    td: ({ children }) => (
      <td className="px-4 py-3 text-db-muted">{children}</td>
    ),
    strong: ({ children }) => (
      <strong className="text-db-text font-semibold">{children}</strong>
    ),
    em: ({ children }) => (
      <em className="text-db-muted italic">{children}</em>
    ),
    ...components,
  }
}
