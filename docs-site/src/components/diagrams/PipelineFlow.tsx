'use client'

import { useCallback, useMemo } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'

interface FlowNode {
  id: string
  label: string
  type?: 'input' | 'output' | 'default' | 'group'
  color?: string
  icon?: string
}

interface FlowEdge {
  source: string
  target: string
  label?: string
  animated?: boolean
  dashed?: boolean
}

interface PipelineFlowProps {
  title?: string
  nodes: FlowNode[]
  edges: FlowEdge[]
  height?: number
}

const NODE_STYLES: Record<string, React.CSSProperties> = {
  default: {
    background: '#121212',
    border: '1px solid #262626',
    borderRadius: '8px',
    padding: '10px 16px',
    color: '#F2F2F2',
    fontSize: '13px',
    fontFamily: 'Inter, sans-serif',
  },
  input: {
    background: '#121212',
    border: '1px solid #AAFF00',
    borderRadius: '8px',
    padding: '10px 16px',
    color: '#F2F2F2',
    fontSize: '13px',
    fontFamily: 'Inter, sans-serif',
  },
  output: {
    background: '#121212',
    border: '1px solid #56B6C2',
    borderRadius: '8px',
    padding: '10px 16px',
    color: '#F2F2F2',
    fontSize: '13px',
    fontFamily: 'Inter, sans-serif',
  },
  group: {
    background: 'rgba(170, 255, 0, 0.03)',
    border: '1px dashed #262626',
    borderRadius: '12px',
    padding: '20px',
    color: '#A0A098',
    fontSize: '12px',
    fontFamily: 'Inter, sans-serif',
  },
}

export function PipelineFlow({ title, nodes: flowNodes, edges: flowEdges, height = 500 }: PipelineFlowProps) {
  const initialNodes: Node[] = useMemo(() =>
    flowNodes.map((n, i) => ({
      id: n.id,
      data: { label: n.label },
      position: { x: (i % 4) * 220 + 40, y: Math.floor(i / 4) * 100 + 40 },
      style: { ...NODE_STYLES[n.type || 'default'], borderColor: n.color || undefined },
      type: n.type === 'group' ? 'group' : 'default',
    })),
    [flowNodes]
  )

  const initialEdges: Edge[] = useMemo(() =>
    flowEdges.map((e, i) => ({
      id: `e-${i}`,
      source: e.source,
      target: e.target,
      label: e.label,
      animated: e.animated,
      style: { stroke: e.dashed ? '#7A7A72' : '#AAFF00', strokeDasharray: e.dashed ? '5 5' : undefined },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#AAFF00', width: 16, height: 16 },
      labelStyle: { fill: '#A0A098', fontSize: 11, fontFamily: 'Inter' },
      labelBgStyle: { fill: '#171717', fillOpacity: 0.9 },
    })),
    [flowEdges]
  )

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  return (
    <div className="my-8 rounded-lg border border-db-border overflow-hidden">
      {title && (
        <div className="px-4 py-2.5 bg-db-surface border-b border-db-border">
          <span className="text-xs font-medium text-db-muted">{title}</span>
        </div>
      )}
      <div style={{ height }} className="bg-db-bg">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          proOptions={{ hideAttribution: true }}
          defaultEdgeOptions={{
            type: 'smoothstep',
            style: { strokeWidth: 2, stroke: '#AAFF00' },
          }}
        >
          <Background color="#262626" gap={20} />
          <Controls
            style={{ background: '#121212', borderColor: '#262626' }}
          />
          <MiniMap
            nodeColor="#262626"
            style={{ background: '#121212', border: '1px solid #262626' }}
            maskColor="rgba(10, 10, 10, 0.7)"
          />
        </ReactFlow>
      </div>
    </div>
  )
}
