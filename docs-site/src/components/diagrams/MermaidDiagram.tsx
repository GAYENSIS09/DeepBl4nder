'use client'

import { useEffect, useRef, useState } from 'react'
import { Expand, Copy, Check } from 'lucide-react'

interface MermaidDiagramProps {
  chart: string
  title?: string
  caption?: string
}

export function MermaidDiagram({ chart, title, caption }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [svg, setSvg] = useState<string>('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function render() {
      const mermaid = (await import('mermaid')).default
      mermaid.initialize({
        startOnLoad: false,
        theme: 'dark',
        themeVariables: {
          primaryColor: '#121212',
          primaryTextColor: '#F2F2F2',
          primaryBorderColor: '#AAFF00',
          lineColor: '#7A7A72',
          secondaryColor: '#171717',
          tertiaryColor: '#0A0A0A',
          fontFamily: 'Inter, sans-serif',
          fontSize: '14px',
        },
        flowchart: {
          useMaxWidth: true,
          htmlLabels: true,
          curve: 'basis',
        },
      })
      if (!chart || typeof chart !== 'string') {
        console.error('MermaidDiagram: chart prop is missing or not a string')
        return
      }
      try {
        const id = `mermaid-${Math.random().toString(36).slice(2, 9)}`
        const { svg: rendered } = await mermaid.render(id, chart.trim())
        if (!cancelled) setSvg(rendered)
      } catch (e) {
        console.error('Mermaid render error:', e)
      }
    }
    render()
    return () => { cancelled = true }
  }, [chart])

  const handleCopy = async () => {
    await navigator.clipboard.writeText(chart.trim())
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="my-8 rounded-lg border border-db-border overflow-hidden">
      {title && (
        <div className="flex items-center justify-between px-4 py-2.5 bg-db-surface border-b border-db-border">
          <span className="text-xs font-medium text-db-muted">{title}</span>
          <div className="flex items-center gap-1">
            <button onClick={handleCopy} className="p-1 text-db-dim hover:text-db-text transition-colors" title="Copy mermaid code">
              {copied ? <Check className="w-3.5 h-3.5 text-db-accent" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      )}
      <div ref={containerRef} className="bg-db-bg p-6 flex justify-center overflow-x-auto [&_svg]:max-w-full">
        {svg ? (
          <div dangerouslySetInnerHTML={{ __html: svg }} className="mermaid-svg" />
        ) : (
          <div className="text-sm text-db-dim animate-pulse">Loading diagram...</div>
        )}
      </div>
      {caption && (
        <div className="px-4 py-2 bg-db-surface/50 border-t border-db-border text-xs text-db-dim text-center">
          {caption}
        </div>
      )}
    </div>
  )
}
