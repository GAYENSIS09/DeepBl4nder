'use client';

import type { ReactNode } from 'react';

import { RequireAuth } from '@/components/RequireAuth';
import { Sidebar } from '@/components/Sidebar';

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <div className="min-h-screen">
        <Sidebar />
        <main className="ml-[200px] min-h-screen">{children}</main>
      </div>
    </RequireAuth>
  );
}
