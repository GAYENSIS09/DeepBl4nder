import { Suspense } from 'react';

import { ProductionStream } from '@/components/ProductionStream';

export default function RealtimePage() {
  return (
    <Suspense fallback={<div className="p-10 text-muted">Chargement…</div>}>
      <ProductionStream />
    </Suspense>
  );
}
