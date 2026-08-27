'use client';

import { useState, useEffect } from 'react';
import { Card, CardHeader, CardBody, Button, Badge } from '@/components/ui';
import { useNotifications } from '@/lib/notifications';

interface Settings {
  llmProvider: string;
  llmModel: string;
  renderEngine: string;
  renderQuality: string;
  renderResolution: string;
  defaultFps: number;
  budgetLimit: number;
  autoApprove: boolean;
  notifications: boolean;
  maxRevisions: number;
  targetLanguages: string;
}

const DEFAULT_SETTINGS: Settings = {
  llmProvider: 'gemini',
  llmModel: 'gemini-2.0-flash',
  renderEngine: 'blender',
  renderQuality: 'medium',
  renderResolution: '1920x1080',
  defaultFps: 24,
  budgetLimit: 1.0,
  autoApprove: false,
  notifications: true,
  maxRevisions: 1,
  targetLanguages: 'fr,en',
};

function loadSettings(): Settings {
  if (typeof window === 'undefined') return DEFAULT_SETTINGS;
  try {
    const raw = localStorage.getItem('deepbl4nder_settings');
    return raw ? { ...DEFAULT_SETTINGS, ...JSON.parse(raw) } : DEFAULT_SETTINGS;
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [saved, setSaved] = useState(false);
  const { notify } = useNotifications();

  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  function handleSave() {
    try {
      localStorage.setItem('deepbl4nder_settings', JSON.stringify(settings));
      setSaved(true);
      notify('success', 'Paramètres sauvegardés.');
      setTimeout(() => setSaved(false), 2000);
    } catch {
      notify('error', 'Erreur lors de la sauvegarde.');
    }
  }

  function handleReset() {
    setSettings(DEFAULT_SETTINGS);
    localStorage.removeItem('deepbl4nder_settings');
    notify('info', 'Paramètres réinitialisés.');
  }

  const update = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    setSettings((s) => ({ ...s, [key]: value }));
    setSaved(false);
  };

  return (
    <div className="animate-fade-up p-6 md:p-10">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold tracking-tight text-off-white">Paramètres</h1>
          <p className="mt-1 text-muted">Configuration de la plateforme et préférences utilisateur.</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={handleReset}>Réinitialiser</Button>
          <Button onClick={handleSave}>
            {saved ? <><Badge tone="green">Sauvegardé</Badge></> : 'Sauvegarder'}
          </Button>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* LLM Configuration */}
        <Card>
          <CardHeader title="Modèle LLM" subtitle="Fournisseur et modèle pour les agents IA." />
          <CardBody>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-off-white mb-1">Fournisseur</label>
                <select
                  value={settings.llmProvider}
                  onChange={(e) => update('llmProvider', e.target.value)}
                  className="w-full rounded-lg border border-border bg-off-black px-3 py-2 text-sm text-off-white focus:border-acid focus:outline-none"
                >
                  <option value="gemini">Google Gemini</option>
                  <option value="groq">Groq</option>
                  <option value="nvidia">NVIDIA NIM</option>
                  <option value="openrouter">OpenRouter</option>
                  <option value="cloudflare">Cloudflare Workers AI</option>
                  <option value="local">Local (Ollama/vLLM)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-off-white mb-1">Modèle</label>
                <select
                  value={settings.llmModel}
                  onChange={(e) => update('llmModel', e.target.value)}
                  className="w-full rounded-lg border border-border bg-off-black px-3 py-2 text-sm text-off-white focus:border-acid focus:outline-none"
                >
                  <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                  <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
                  <option value="llama-3.3-70b">Llama 3.3 70B (Groq)</option>
                  <option value="qwen3.6-27b">Qwen 3.6 27B (Groq)</option>
                  <option value="gpt-oss-120b">GPT-OSS 120B (Groq)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-off-white mb-1">Languages cibles (virgule)</label>
                <input
                  type="text"
                  value={settings.targetLanguages}
                  onChange={(e) => update('targetLanguages', e.target.value)}
                  placeholder="fr,en,wo"
                  className="w-full rounded-lg border border-border bg-off-black px-3 py-2 text-sm text-off-white focus:border-acid focus:outline-none font-mono"
                />
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Render Configuration */}
        <Card>
          <CardHeader title="Moteur de rendu" subtitle="Moteur 3D et qualité de rendu par défaut." />
          <CardBody>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-off-white mb-1">Moteur</label>
                <select
                  value={settings.renderEngine}
                  onChange={(e) => update('renderEngine', e.target.value)}
                  className="w-full rounded-lg border border-border bg-off-black px-3 py-2 text-sm text-off-white focus:border-acid focus:outline-none"
                >
                  <option value="blender">Blender (EEVEE/Cycles)</option>
                  <option value="unreal">Unreal Engine 5</option>
                  <option value="godot">Godot 4</option>
                  <option value="ai-video">AI Video (CogVideoX)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-off-white mb-1">Qualité</label>
                <select
                  value={settings.renderQuality}
                  onChange={(e) => update('renderQuality', e.target.value)}
                  className="w-full rounded-lg border border-border bg-off-black px-3 py-2 text-sm text-off-white focus:border-acid focus:outline-none"
                >
                  <option value="draft">Brouillon (rapide)</option>
                  <option value="medium">Moyen</option>
                  <option value="high">Haute</option>
                  <option value="ultra">Ultra (lent)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-off-white mb-1">Résolution</label>
                <select
                  value={settings.renderResolution}
                  onChange={(e) => update('renderResolution', e.target.value)}
                  className="w-full rounded-lg border border-border bg-off-black px-3 py-2 text-sm text-off-white focus:border-acid focus:outline-none"
                >
                  <option value="1280x720">720p (1280×720)</option>
                  <option value="1920x1080">1080p (1920×1080)</option>
                  <option value="2560x1440">1440p (2560×1440)</option>
                  <option value="3840x2160">4K (3840×2160)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-off-white mb-1">FPS</label>
                <input
                  type="number"
                  value={settings.defaultFps}
                  onChange={(e) => update('defaultFps', parseInt(e.target.value) || 24)}
                  min={12}
                  max={60}
                  className="w-full rounded-lg border border-border bg-off-black px-3 py-2 text-sm text-off-white focus:border-acid focus:outline-none"
                />
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Budget */}
        <Card>
          <CardHeader title="Budget" subtitle="Limites de coût et révisions par production." />
          <CardBody>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-off-white mb-1">Budget max par production ($)</label>
                <input
                  type="number"
                  value={settings.budgetLimit}
                  onChange={(e) => update('budgetLimit', parseFloat(e.target.value) || 1.0)}
                  min={0.1}
                  max={100}
                  step={0.1}
                  className="w-full rounded-lg border border-border bg-off-black px-3 py-2 text-sm text-off-white focus:border-acid focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-off-white mb-1">Révisions max (QA)</label>
                <input
                  type="number"
                  value={settings.maxRevisions}
                  onChange={(e) => update('maxRevisions', parseInt(e.target.value) || 1)}
                  min={0}
                  max={5}
                  className="w-full rounded-lg border border-border bg-off-black px-3 py-2 text-sm text-off-white focus:border-acid focus:outline-none"
                />
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Workflow */}
        <Card>
          <CardHeader title="Workflow" subtitle="Préférences de workflow et notifications." />
          <CardBody>
            <div className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.autoApprove}
                  onChange={(e) => update('autoApprove', e.target.checked)}
                  className="h-4 w-4 rounded border-border bg-off-black text-acid focus:ring-acid/60"
                />
                <div>
                  <span className="text-sm font-medium text-off-white">Approbation automatique</span>
                  <p className="text-xs text-muted">Approuver automatiquement les étapes sans intervention humaine.</p>
                </div>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.notifications}
                  onChange={(e) => update('notifications', e.target.checked)}
                  className="h-4 w-4 rounded border-border bg-off-black text-acid focus:ring-acid/60"
                />
                <div>
                  <span className="text-sm font-medium text-off-white">Notifications</span>
                  <p className="text-xs text-muted">Recevoir des notifications quand les productions sont terminées.</p>
                </div>
              </label>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
