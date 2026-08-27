'use client';

import type { ReactNode } from 'react';

import { RequireAuth } from '@/components/RequireAuth';
import { Sidebar } from '@/components/Sidebar';

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <div className="min-h-screen">
        <Sidebar />
        <main className="min-h-screen lg:ml-[200px]">{children}</main>
      </div>
    </RequireAuth>
  );
}
