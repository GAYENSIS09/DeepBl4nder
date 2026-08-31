import Sidebar from '@/components/Sidebar'

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 min-w-0 max-w-4xl px-6 sm:px-10 py-14">
        <div className="prose-db">{children}</div>
      </main>
    </div>
  )
}
