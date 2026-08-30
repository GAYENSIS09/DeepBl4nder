import Sidebar from '@/components/Sidebar'

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-db-bg">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="max-w-3xl px-10 py-14">{children}</div>
      </main>
    </div>
  )
}



