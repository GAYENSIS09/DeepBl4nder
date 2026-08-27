'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardBody, Badge, EmptyState, Button, Skeleton } from '@/components/ui';
import { useNotifications } from '@/lib/notifications';

interface Asset {
  name: string;
  type: string;
  path: string;
  size: number;
  source: string;
  created_at: string;
}

const ASSET_ICONS: Record<string, string> = {
  model: '🧊',
  texture: '🎨',
  hdri: '🌅',
  audio: '🎵',
  script: '📄',
  render: '🎬',
  unknown: '📦',
};

export default function LibraryPage() {
  const [activeTab, setActiveTab] = useState<'assets' | 'templates' | 'skills'>('assets');
  const { notify } = useNotifications();

  return (
    <div className="animate-fade-up p-6 md:p-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold tracking-tight text-off-white">Bibliothèque</h1>
        <p className="mt-1 text-muted">Assets, productions sauvegardées, skills et templates réutilisables.</p>
      </header>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 border-b border-border">
        {([
          { key: 'assets' as const, label: 'Assets 3D', icon: '🧊' },
          { key: 'templates' as const, label: 'Templates', icon: '📋' },
          { key: 'skills' as const, label: 'Skills IA', icon: '🧠' },
        ]).map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.key
                ? 'border-acid text-acid'
                : 'border-transparent text-muted hover:text-off-white'
            }`}
          >
            <span className="text-xs">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'assets' && <AssetsTab />}
      {activeTab === 'templates' && <TemplatesTab />}
      {activeTab === 'skills' && <SkillsTab />}
    </div>
  );
}

function AssetsTab() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Assets 3D"
          subtitle="PolyHaven, bibliothèque locale et assets importés."
          actions={<Button variant="outline" className="text-xs">Importer</Button>}
        />
        <CardBody>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { name: 'PolyHaven HDRIs', desc: 'Environnements HDRI haute qualité (CC0)', count: '1000+' },
              { name: 'Quaternius Models', desc: 'Modèles de personnages animés (CC0)', count: '200+' },
              { name: 'Scripts Blender', desc: 'Scripts générés par les agents IA', count: '—' },
            ].map((source) => (
              <div key={source.name} className="rounded-lg border border-border bg-off-black p-4">
                <div className="flex items-start justify-between">
                  <h3 className="text-sm font-medium text-off-white">{source.name}</h3>
                  <Badge tone="acid">{source.count}</Badge>
                </div>
                <p className="mt-1 text-xs text-muted">{source.desc}</p>
              </div>
            ))}
          </div>
        </CardBody>
      </Card>
    </div>
  );
}

function TemplatesTab() {
  const templates = [
    { name: 'Cyberpunk Alley', desc: 'Ruelle néon cyberpunk avec pluie et néons', tags: ['blender', 'cyberpunk'] },
    { name: 'Dark Forest', desc: 'Forêt sombre et brumeuse avec éclairage dramatique', tags: ['blender', 'nature'] },
    { name: 'Studio Interview', desc: 'Setup studio pour interviews ou présentations', tags: ['blender', 'studio'] },
  ];

  return (
    <Card>
      <CardHeader title="Templates" subtitle="Scènes prédéfinies et presets de production réutilisables." />
      <CardBody>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {templates.map((t) => (
            <div key={t.name} className="rounded-lg border border-border bg-off-black p-4 transition-colors hover:border-acid/30">
              <h3 className="text-sm font-medium text-off-white">{t.name}</h3>
              <p className="mt-1 text-xs text-muted">{t.desc}</p>
              <div className="mt-3 flex flex-wrap gap-1">
                {t.tags.map((tag) => (
                  <Badge key={tag} tone="muted">{tag}</Badge>
                ))}
              </div>
            </div>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}

function SkillsTab() {
  const skills = [
    { name: 'storytelling', desc: 'Structure narrative, acts, beats, dialogues', category: 'Narration' },
    { name: 'blender-python', desc: 'Scripting Blender via bpy', category: 'Rendu' },
    { name: 'character-design', desc: 'Conception de personnages 3D', category: 'Assets' },
    { name: 'lighting', desc: 'Éclairage et ambiance de scène', category: 'Rendu' },
    { name: 'animation', desc: 'Animation de personnages et objets', category: 'Animation' },
    { name: 'sound-design', desc: 'Conception sonore et effets', category: 'Audio' },
    { name: 'music', desc: 'Composition musicale adaptative', category: 'Audio' },
    { name: 'compositing', desc: 'Post-rendu et étalonnage', category: 'Post-prod' },
    { name: 'rendering', desc: 'Paramètres de rendu et optimisation', category: 'Rendu' },
    { name: 'cinematography', desc: 'Cadrage, mouvements de caméra', category: 'Rendu' },
  ];

  const categories = [...new Set(skills.map((s) => s.category))];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Skills IA"
          subtitle={`${skills.length} skills chargés pour les agents NOOA. Les skills guident la génération de code et de specs.`}
        />
        <CardBody>
          {categories.map((cat) => (
            <div key={cat} className="mb-6 last:mb-0">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">{cat}</h3>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {skills
                  .filter((s) => s.category === cat)
                  .map((skill) => (
                    <div key={skill.name} className="flex items-center gap-2 rounded-lg border border-border bg-off-black px-3 py-2">
                      <Badge tone="acid" className="shrink-0">{skill.name}</Badge>
                      <span className="text-xs text-muted truncate">{skill.desc}</span>
                    </div>
                  ))}
              </div>
            </div>
          ))}
        </CardBody>
      </Card>
    </div>
  );
}
