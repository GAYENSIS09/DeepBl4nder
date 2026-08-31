export function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-flex items-center px-1.5 py-0.5 text-[11px] font-mono font-semibold text-db-text bg-db-surface border border-db-border rounded shadow-sm">
      {children}
    </kbd>
  )
}
