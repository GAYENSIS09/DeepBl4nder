import { File, Folder, FolderOpen } from 'lucide-react'

interface FileTreeItemProps {
  name: string
  type: 'file' | 'folder'
  children?: React.ReactNode
  badge?: string
}

export function FileTreeItem({ name, type, children, badge }: FileTreeItemProps) {
  const Icon = type === 'folder' ? Folder : File
  return (
    <div className="my-0.5">
      <div className="flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-db-surface/50 rounded">
        <Icon className={`w-4 h-4 ${type === 'folder' ? 'text-db-accent' : 'text-db-dim'}`} />
        <span className="text-db-text font-mono text-xs">{name}</span>
        {badge && (
          <span className="text-[9px] uppercase tracking-wider text-db-accent bg-db-accent/10 px-1.5 py-0.5 rounded">
            {badge}
          </span>
        )}
      </div>
      {children && <div className="pl-5 border-l border-db-border ml-2">{children}</div>}
    </div>
  )
}

interface FileTreeProps {
  children: React.ReactNode
}

export function FileTree({ children }: FileTreeProps) {
  return (
    <div className="my-6 rounded-lg border border-db-border bg-db-surface/30 p-2 font-mono text-sm">
      {children}
    </div>
  )
}
