'use client';

import { useState } from 'react';
import { Card, CardHeader, CardBody, Badge, EmptyState } from '@/components/ui';

interface Asset {
  name: string;
  type: string;
  path: string;
  size: number;
}

export default function LibraryPage() {
  const [activeTab, setActiveTab] = useState<'assets' | 'templates'>('assets');

  return (
    <div className="animate-fade-up p-6 md:p-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold tracking-tight text-off-white">Bibliothèque</h1>
        <p className="mt-1 text-muted">Assets, productions sauvegardées et templates réutilisables.</p>
      </header>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 border-b border-border">
        {(['assets', 'templates'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab
                ? 'border-acid text-acid'
                : 'border-transparent text-muted hover:text-off-white'
            }`}
          >
            {tab === 'assets' ? 'Assets 3D' : 'Templates'}
          </button>
        ))}
      </div>

      {activeTab === 'assets' && (
        <Card>
          <CardHeader title="Assets 3D" subtitle="PolyHaven, bibliothèque locale et assets importés." />
          <CardBody>
            <EmptyState
              title="Aucun asset pour le moment"
              description="Les assets 3D téléchargés depuis PolyHaven ou importés manuellement apparaîtront ici."
            />
          </CardBody>
        </Card>
      )}

      {activeTab === 'templates' && (
        <Card>
          <CardHeader title="Templates" subtitle="Scènes prédéfinies et presets de production réutilisables." />
          <CardBody>
            <EmptyState
              title="Aucun template"
              description="Créez des templates à partir de vos productions pour réutiliser les configurations."
            />
          </CardBody>
        </Card>
      )}
    </div>
  );
}
