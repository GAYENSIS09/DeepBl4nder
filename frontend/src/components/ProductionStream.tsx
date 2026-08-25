'use client';

import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useSearchParams } from 'next/navigation';

import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { useNotifications } from '@/lib/notifications';
import { useProductionStream } from '@/hooks/useProductionStream';
import { useProductionTree } from '@/hooks/useProductionTree';
import type { SSEEvent, SSEStatus } from '@/lib/sse';
import type { ArtifactOut, TimelineOut } from '@/lib/api';
import { Badge, Button, Card, CardBody, CardHeader, EmptyState, Field, Select, Skeleton, Spinner, TextArea, Tabs, TabList, TabTrigger, TabContent } from '@/components/ui';
import { AudioPlayer, CodeViewer, ImagePlayer, JsonViewer, VideoPlayer } from '@/components/ArtifactViewers';
import { fmtCost, fmtSize } from '@/lib/format';

const EVENT_META: Record<string, { label: string; tone: 'green' | 'amber' | 'red' | 'blue' | 'acid' | 'muted' }> = {
  run_started: { label: 'Run démarré', tone: 'blue' },
  run_completed: { label: 'Run terminé', tone: 'green' },
  run_blocked: { label: 'Run bloqué', tone: 'amber' },
  run_failed: { label: 'Run échoué', tone: 'red' },
  step_started: { label: 'Étape démarrée', tone: 'blue' },
  step_completed: { label: 'Étape terminée', tone: 'green' },
  step_resumed: { label: 'Étape reprise (checkpoint)', tone: 'acid' },
  step_failed: { label: 'Étape échouée', tone: 'red' },
  approval_requested: { label: 'Approbation requise', tone: 'amber' },
  approval_granted: { label: 'Approbation accordée', tone: 'green' },
  approval_rejected: { label: 'Approbation refusée', tone: 'red' },
  revision_requested: { label: 'Révision demandée', tone: 'blue' },
  cost_recorded: { label: 'Coût enregistré', tone: 'acid' },
  budget_alert: { label: 'Alerte budget', tone: 'red' },
  llm_call: { label: 'Appel LLM', tone: 'blue' },
};

const STEP_ICONS: Record<string, string> = {
  director: '🎬',
  blender: '🧊',
  qa: '🔍',
  audio: '🎵',
  compositing: '🎨',
  localization: '🌍',
};

const VIEWABLE_TYPES = new Set(['image', 'video', 'audio', 'text']);
const IMAGE_EXTS = new Set(['.png', '.jpg', '.jpeg', '.webp', '.gif', '.exr', '.tiff']);
const VIDEO_EXTS = new Set(['.mp4', '.mov', '.webm']);
const AUDIO_EXTS = new Set(['.wav', '.mp3', '.flac', '.ogg']);
const TEXT_EXTS = new Set(['.json', '.py', '.yaml', '.yml', '.toml', '.txt', '.md', '.csv', '.xml', '.html', '.css', '.js', '.ts', '.jsx', '.tsx', '.sh', '.bat', '.cfg', '.ini', '.conf', '.log', '.srt', '.vtt', '.ass', '.obj', '.fbx', '.blend']);

function artifactViewType(artifact: ArtifactOut): 'image' | 'video' | 'audio' | 'text' | null {
  const ext = '.' + artifact.name.split('.').pop()?.toLowerCase();
  if (IMAGE_EXTS.has(ext)) return 'image';
  if (VIDEO_EXTS.has(ext)) return 'video';
  if (AUDIO_EXTS.has(ext)) return 'audio';
  if (TEXT_EXTS.has(ext)) return 'text';
  return null;
}

function eventSummary(event: SSEEvent): string {
  const parts: string[] = [];
  if (typeof event.agent === 'string') parts.push(event.agent);
  if (typeof event.model === 'string') {
    const modelShort = event.model.split('/').pop() ?? event.model;
    // Le backend rapporte le vainqueur réel du vote routeur (`provider`) ;
    // sans lui, on retombe sur le modèle seul.
    parts.push(typeof event.provider === 'string' ? `${event.provider} · ${modelShort}` : modelShort);
  } else if (typeof event.provider === 'string') {
    parts.push(event.provider);
  }
  if (typeof event.elapsed_s === 'number') parts.push(`${event.elapsed_s}s`);
  if (typeof event.score === 'number') parts.push(`score ${(event.score * 100).toFixed(0)}%`);
  if (typeof event.languages === 'string') parts.push(event.languages);
  if (typeof event.output === 'string') parts.push(event.output.split('/').pop() ?? event.output);
  if (typeof event.cost === 'number') parts.push(`coût ${fmtCost(event.cost)}`);
  if (typeof event.target_step === 'string') parts.push(`cible : ${event.target_step}`);
  if (typeof event.revision === 'number') parts.push(`révision #${event.revision}`);
  if (typeof event.error === 'string') parts.push(event.error.slice(0, 200));
  return parts.join(' · ');
}

function eventTime(event: SSEEvent): string {
  const ts = typeof event.ts === 'number' ? event.ts * 1000 : NaN;
  return Number.isFinite(ts)
    ? new Date(ts).toLocaleTimeString('fr-FR')
    : new Date().toLocaleTimeString('fr-FR');
}

function statusBadge(status: SSEStatus, heartbeatText: string): ReactNode {
  const dot = 'inline-block h-2 w-2 rounded-full';
  switch (status.state) {
    case 'connected':
      return (
        <Badge tone="green">
          <span className={`${dot} bg-green-400 animate-pulse`} />
          Connecté · {heartbeatText}
        </Badge>
      );
    case 'connecting':
      return (
        <Badge tone="blue">
          <span className={`${dot} bg-blue-400 animate-pulse`} />
          Connexion…
        </Badge>
      );
    case 'reconnecting':
      return (
        <Badge tone="red">
          <span className={`${dot} bg-red-500 animate-pulse`} />
          Reconnexion SSE en cours… (essai {status.attempt}) dans {(status.delayMs / 1000).toFixed(0)} s
        </Badge>
      );
    case 'error':
      return (
        <Badge tone="red">
          <span className={`${dot} bg-red-500`} />
          {status.message}
        </Badge>
      );
    default:
      return (
        <Badge tone="muted">
          <span className={`${dot} bg-muted`} />
          Déconnecté
        </Badge>
      );
  }
}

/* ------------------------------------------------------------------ */
/* Timeline View                                                       */
/* ------------------------------------------------------------------ */

interface TimelineViewProps {
  timeline: TimelineOut;
  patchTargets: Record<string, { target: string; newValue: string; rationale: string }>;
  onPatchTargetChange: (shotId: string, field: string, value: string) => void;
  onSubmitPatch: (shotId: string, target: string, newValue: any, rationale: string) => void;
  patchBusy: string | null;
}

function TimelineView({
  timeline,
  patchTargets,
  onPatchTargetChange,
  onSubmitPatch,
  patchBusy,
}: TimelineViewProps) {
  const shotStatusTone: Record<string, 'green' | 'amber' | 'red' | 'blue' | 'acid' | 'muted'> = {
    planned: 'muted',
    pending: 'blue',
    running: 'acid',
    completed: 'green',
    failed: 'red',
    blocked: 'amber',
  };

  return (
    <div className="space-y-4">
      {timeline.sequences.map((seq) => (
        <Card key={seq.id} className="overflow-hidden border-t border-border/50">
          <CardHeader
            title={`Séquence ${seq.order_index + 1}: ${seq.name}`}
            subtitle={`${seq.scenes.length} scène(s)`}
          />
          <CardBody className="space-y-3 p-0">
            {seq.scenes.map((scene) => (
              <div key={scene.id} className="border-t border-border/30">
                <div className="px-4 py-2 bg-off-black/30 font-medium text-sm text-off-white">
                  Scène {scene.order_index + 1}: {scene.name} ({scene.shots.length} plan(s))
                </div>
                <ul className="divide-y divide-border/30">
                  {scene.shots.map((shot) => (
                    <li
                      key={shot.id}
                      className="flex flex-col sm:flex-row sm:items-center gap-3 px-4 py-3 hover:bg-off-black/30"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center gap-3 flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-muted w-12 text-right">#{shot.index + 1}</span>
                          <Badge tone={shotStatusTone[shot.status] ?? 'muted'}>
                            {shot.status}
                          </Badge>
                        </div>
                        <div className="flex-1 min-w-0 space-y-1">
                          {shot.camera_summary && (
                            <p className="truncate text-sm text-muted font-mono">
                              📷 {shot.camera_summary}
                            </p>
                          )}
                          {shot.action && (
                            <p className="truncate text-sm text-off-white/80">{shot.action}</p>
                          )}
                          <p className="truncate text-xs text-muted">
                            {shot.start.toFixed(1)}s → {shot.end.toFixed(1)}s ({(
                              shot.end - shot.start
                            ).toFixed(1)}s)
                          </p>
                        </div>
                        <PatchForm
                          shotId={shot.id}
                          shotIndex={shot.index}
                          patchTargets={patchTargets}
                          onPatchTargetChange={onPatchTargetChange}
                          onSubmitPatch={onSubmitPatch}
                          patchBusy={patchBusy}
                        />
                      </div>
                      </li>
                    ))}
                </ul>
              </div>
            ))}
          </CardBody>
        </Card>
      ))}
    </div>
  );
}

interface PatchFormProps {
  shotId: string;
  shotIndex: number;
  patchTargets: Record<string, { target: string; newValue: string; rationale: string }>;
  onPatchTargetChange: (shotId: string, field: string, value: string) => void;
  onSubmitPatch: (shotId: string, target: string, newValue: any, rationale: string) => void;
  patchBusy: string | null;
}

function PatchForm({
  shotId,
  shotIndex,
  patchTargets,
  onPatchTargetChange,
  onSubmitPatch,
  patchBusy,
}: PatchFormProps) {
  const target = patchTargets[shotId]?.target || `shots[${shotIndex}].camera_summary`;
  const newValue = patchTargets[shotId]?.newValue || '';
  const rationale = patchTargets[shotId]?.rationale || '';

  return (
    <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-80">
      <Select
        value={target}
        onChange={(e) => onPatchTargetChange(shotId, 'target', e.target.value)}
        className="flex-1 min-w-[150px]"
      >
        <option value={`shots[${shotIndex}].camera_summary`}>camera_summary</option>
        <option value={`shots[${shotIndex}].action`}>action</option>
        <option value={`shots[${shotIndex}].camera_angle`}>camera_angle</option>
        <option value={`shots[${shotIndex}].camera_movement`}>camera_movement</option>
        <option value={`shots[${shotIndex}].duration`}>duration</option>
        <option value={`shots[${shotIndex}].transition`}>transition</option>
        <option value={`shots[${shotIndex}].visual_notes`}>visual_notes</option>
      </Select>
      <input
        type="text"
        placeholder="Nouvelle valeur"
        value={newValue}
        onChange={(e) => onPatchTargetChange(shotId, 'newValue', e.target.value)}
        className="flex-1 min-w-[120px] px-2 py-1 text-sm bg-black/50 border border-border rounded"
      />
      <input
        type="text"
        placeholder="Raison (optionnel)"
        value={rationale}
        onChange={(e) => onPatchTargetChange(shotId, 'rationale', e.target.value)}
        className="flex-1 min-w-[120px] px-2 py-1 text-sm bg-black/50 border border-border rounded"
      />
      <Button
        className="px-3 py-1.5 text-xs"
        onClick={() => onSubmitPatch(shotId, target, newValue, rationale)}
        disabled={patchBusy === shotId || !newValue.trim()}
      >
        {patchBusy === shotId ? <span className="h-3 w-3 animate-spin border-t-current rounded-full" /> : 'Patch'}
      </Button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Artifact Viewer (inline modal)                                      */
/* ------------------------------------------------------------------ */

function ArtifactViewer({
  artifact,
  productionId,
  onClose,
}: {
  artifact: ArtifactOut;
  productionId: string;
  onClose: () => void;
}) {
  const { notify } = useNotifications();
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const viewType = artifactViewType(artifact);

  useEffect(() => {
    let revoke: string | null = null;
    setLoading(true);
    setTextContent(null);
    api
      .getArtifactBlob(productionId, artifact.path)
      .then(async (blob) => {
        if (viewType === 'text') {
          const text = await blob.text();
          setTextContent(text);
        } else {
          const url = URL.createObjectURL(blob);
          revoke = url;
          setBlobUrl(url);
        }
      })
      .catch(() => {
        notify('error', 'Impossible de charger l\'artifact.');
        onClose();
      })
      .finally(() => setLoading(false));
    return () => {
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [productionId, artifact.path, viewType]);

  const handleCopy = async () => {
    if (!textContent) return;
    try {
      await navigator.clipboard.writeText(textContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      notify('error', 'Copie impossible.');
    }
  };

  const langHint = artifact.name.endsWith('.py')
    ? 'python'
    : artifact.name.endsWith('.json')
      ? 'json'
      : artifact.name.endsWith('.yaml') || artifact.name.endsWith('.yml')
        ? 'yaml'
        : artifact.name.endsWith('.md')
          ? 'markdown'
          : artifact.name.endsWith('.html')
            ? 'html'
            : artifact.name.endsWith('.css')
              ? 'css'
              : artifact.name.endsWith('.js') || artifact.name.endsWith('.ts') || artifact.name.endsWith('.jsx') || artifact.name.endsWith('.tsx')
                ? 'javascript'
                : artifact.name.endsWith('.sh')
                  ? 'bash'
                  : 'text';

  const jsonData = useMemo<unknown | null | undefined>(() => {
    if (langHint !== 'json' || textContent === null) return null;
    try {
      return JSON.parse(textContent) as unknown;
    } catch {
      return undefined; // JSON invalide -> repli code
    }
  }, [langHint, textContent]);

  const isJson = langHint === 'json' && jsonData !== null && jsonData !== undefined;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in p-4"
      onClick={onClose}
    >
      <div
        className="relative flex h-full max-h-full w-full max-w-5xl flex-col overflow-hidden rounded-xl border border-border bg-off-black"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-3 py-2 sm:px-4 sm:py-3 shrink-0 gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <p className="truncate font-mono text-sm text-off-white">{artifact.name}</p>
            <Badge tone="muted" className="hidden sm:inline-flex">{isJson ? 'json · interactif' : langHint}</Badge>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            {viewType === 'text' && textContent !== null && !isJson ? (
              <Button variant="outline" className="px-2 py-1 text-xs" onClick={() => void handleCopy()}>
                {copied ? 'Copié !' : 'Copier'}
              </Button>
            ) : null}
            <Badge tone="muted" className="hidden sm:inline-flex">{artifact.type}</Badge>
            <Button variant="ghost" onClick={onClose} className="px-2 py-1 text-xs">
              Fermer
            </Button>
          </div>
        </div>
        <div className="flex-1 overflow-auto p-2 sm:p-4 min-h-0 flex flex-col">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Spinner className="border-t-acid h-8 w-8" />
            </div>
          ) : viewType === 'text' && textContent !== null ? (
            isJson ? (
              <JsonViewer data={jsonData} filename={artifact.name} />
            ) : (
              <CodeViewer content={textContent} />
            )
          ) : viewType === 'video' && blobUrl ? (
            <VideoPlayer url={blobUrl} filename={artifact.name} />
          ) : viewType === 'audio' && blobUrl ? (
            <AudioPlayer url={blobUrl} filename={artifact.name} />
          ) : viewType === 'image' && blobUrl ? (
            <ImagePlayer url={blobUrl} filename={artifact.name} />
          ) : (
            <p className="py-12 text-center text-sm text-muted">Aperçu non supporté pour ce type de fichier.</p>
          )}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main component                                                     */
/* ------------------------------------------------------------------ */

export function ProductionStream({ initialProductionId }: { initialProductionId?: string }) {
  const searchParams = useSearchParams();
  const { token } = useAuth();
  const { notify } = useNotifications();
  const { productions } = useProductionTree(5000);

  const [productionId, setProductionId] = useState<string | null>(
    () => initialProductionId ?? searchParams.get('production'),
  );
  const [runBusy, setRunBusy] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  const [revisionStep, setRevisionStep] = useState('director');
  const [revisionComment, setRevisionComment] = useState('');
  const [revisionBusy, setRevisionBusy] = useState(false);
  const [revisionError, setRevisionError] = useState<string | null>(null);

  const [artifacts, setArtifacts] = useState<ArtifactOut[]>([]);
  const [artifactsLoading, setArtifactsLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<{ url: string; isVideo: boolean } | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);

  const [viewingArtifact, setViewingArtifact] = useState<ArtifactOut | null>(null);
  const [deleteBusy, setDeleteBusy] = useState<string | null>(null);

  // Timeline & patches
  const [timeline, setTimeline] = useState<TimelineOut | null>(null);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [patchTargets, setPatchTargets] = useState<Record<string, { target: string; newValue: string; rationale: string }>>({});
  const [patchBusy, setPatchBusy] = useState<string | null>(null);

  const { events, status, lastHeartbeatAt, reconnect } = useProductionStream(productionId, token);

  const refreshTimeline = useCallback(() => {
    if (!productionId) return;
    setTimelineLoading(true);
    api
      .getTimeline(productionId)
      .then(setTimeline)
      .catch(() => setTimeline(null))
      .finally(() => setTimelineLoading(false));
  }, [productionId]);

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 5000);
    return () => window.clearInterval(id);
  }, []);

  const refreshArtifacts = useCallback(() => {
    if (!productionId) return;
    setArtifactsLoading(true);
    api
      .listArtifacts(productionId)
      .then(setArtifacts)
      .catch(() => setArtifacts([]))
      .finally(() => setArtifactsLoading(false));
  }, [productionId]);

  useEffect(() => {
    if (!productionId) {
      setArtifacts([]);
      setPreviewUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev.url);
        return null;
      });
      setTimeline(null);
      return;
    }
    refreshArtifacts();
    refreshTimeline();
  }, [productionId, events.length, refreshArtifacts, refreshTimeline]);

  const handleApproval = async () => {
    if (!productionId) return;
    try {
      await api.approveProduction(productionId);
      notify('success', 'Production approuvée — le run continue.');
      refreshTimeline();
    } catch (err) {
      notify('error', err instanceof Error ? err.message : 'Approbation impossible.');
    }
  };

  const handlePatch = async (shotId: string, target: string, newValue: any, rationale: string) => {
    if (!productionId) return;
    setPatchBusy(shotId);
    try {
      await api.createPatch(productionId, { target, old_value: null, new_value: newValue, rationale });
      notify('success', `Patch créé pour ${target} — s'appliquera au prochain run.`);
      setPatchTargets((prev) => ({ ...prev, [shotId]: { target, newValue: '', rationale: '' } }));
    } catch (err) {
      notify('error', err instanceof Error ? err.message : 'Patch impossible.');
    } finally {
      setPatchBusy(null);
    }
  };

  const handleRevision = async () => {
    if (!productionId) return;
    setRevisionBusy(true);
    setRevisionError(null);
    try {
      await api.requestRevision(productionId, {
        target_step: revisionStep || 'director',
        comment: revisionComment,
      });
      notify('success', `Révision demandée sur « ${revisionStep || 'director'} ».`);
      setRevisionComment('');
    } catch (err) {
      setRevisionError(err instanceof Error ? err.message : 'Révision impossible.');
      notify('error', err instanceof Error ? err.message : 'Révision impossible.');
    } finally {
      setRevisionBusy(false);
    }
  };

  const handleDownload = async (artifact: ArtifactOut) => {
    if (!productionId) return;
    try {
      const { blob, filename } = await api.downloadArtifact(productionId, artifact.path);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      notify('error', err instanceof Error ? err.message : 'Téléchargement impossible.');
    }
  };

  const handleDeleteArtifact = async (artifact: ArtifactOut) => {
    if (!productionId) return;
    if (!confirm(`Supprimer « ${artifact.name} » ? Cette action est irréversible.`)) return;
    setDeleteBusy(artifact.path);
    try {
      await api.deleteArtifact(productionId, artifact.path);
      notify('success', `« ${artifact.name} » supprimé.`);
      refreshArtifacts();
    } catch (err) {
      notify('error', err instanceof Error ? err.message : 'Suppression impossible.');
    } finally {
      setDeleteBusy(null);
    }
  };

  const handlePreview = async () => {
    if (!productionId) return;
    setPreviewBusy(true);
    try {
      const { blob } = await api.preview(productionId);
      setPreviewUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev.url);
        return { url: URL.createObjectURL(blob), isVideo: blob.type.startsWith('video/') };
      });
    } catch (err) {
      setPreviewUrl(null);
      notify('error', err instanceof Error ? err.message : 'Aucun rendu disponible.');
    } finally {
      setPreviewBusy(false);
    }
  };

  const selected = useMemo(
    () => productions.find((p) => p.production.id === productionId) ?? null,
    [productions, productionId],
  );

  const heartbeatText =
    lastHeartbeatAt !== null
      ? `heartbeat il y a ${Math.max(0, Math.round((now - lastHeartbeatAt) / 1000))} s`
      : 'heartbeat —';

  const handleRun = async () => {
    if (!productionId) return;
    setRunBusy(true);
    try {
      await api.runProduction(productionId);
      notify('success', 'Run relancé — le flux se met à jour.');
    } catch (err) {
      notify('error', err instanceof Error ? err.message : 'Lancement impossible.');
    } finally {
      setRunBusy(false);
    }
  };

  const handleCancel = async () => {
    if (!productionId) return;
    if (!confirm('Arrêter cette production en cours ?')) return;
    try {
      await api.cancelProduction(productionId);
      notify('success', 'Production arrêtée.');
    } catch (err) {
      notify('error', err instanceof Error ? err.message : 'Arrêt impossible.');
    }
  };

  const isRunning = selected && (selected.production.status === 'running' || selected.production.status === 'queued');

  return (
    <div className="animate-fade-up p-4 sm:p-6 md:p-10">
      <header className="mb-6 sm:mb-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between sm:gap-4">
        <div>
          <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-off-white">Temps réel</h1>
          <p className="mt-1 text-sm sm:text-base text-muted">Suivi live de la pipeline : étapes, coûts, approbations.</p>
        </div>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
          <Select
            aria-label="Production"
            className="w-full sm:w-72"
            value={productionId ?? ''}
            onChange={(e) => setProductionId(e.target.value || null)}
          >
            <option value="">— Sélectionner une production —</option>
            {productions.map((item) => (
              <option key={item.production.id} value={item.production.id}>
                {item.production.name} ({item.production.status})
              </option>
            ))}
          </Select>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => reconnect()} disabled={!productionId} className="flex-1 sm:flex-none">
              Reconnecter
            </Button>
            {isRunning ? (
              <Button
                variant="ghost"
                onClick={() => void handleCancel()}
                disabled={!productionId}
                className="flex-1 sm:flex-none text-amber-400 hover:text-amber-300 hover:bg-amber-500/10"
              >
                Arrêter
              </Button>
            ) : null}
            <Button onClick={() => void handleRun()} disabled={!productionId || runBusy || !!isRunning} className="flex-1 sm:flex-none">
              {runBusy ? <Spinner className="border-t-black" /> : 'Relancer le run'}
            </Button>
          </div>
        </div>
      </header>

      {!productionId ? (
        <EmptyState
          title="Aucune production sélectionnée"
          description="Choisissez une production dans la liste, ou lancez-en une nouvelle depuis le pipeline."
        />
      ) : (
        <>
          <Card className="mb-6">
            <CardHeader
              title={selected?.production.name ?? 'Production'}
              subtitle={
                selected
                  ? `${selected.production.status} · version ${selected.production.version} · ${fmtCost(selected.production.cost)}`
                  : undefined
              }
              actions={
                <>
                  {statusBadge(status, heartbeatText)}
                  {selected && (selected.production.status === 'waiting_approval' || selected.production.status === 'awaiting_approval') && (
                    <Button
                      variant="outline"
                      className="ml-2 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20"
                      onClick={() => void handleApproval()}
                    >
                      ✓ Approuver & continuer
                    </Button>
                  )}
                </>
              }
            />
            <CardBody className="space-y-3">
              <p className="text-sm text-muted">État : {status.state === 'connected' ? 'flux actif' : 'flux suspendu'}</p>
              <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
                <span>{events.length} événement(s) affichés</span>
                {selected && <span className="font-mono">{selected.production.id}</span>}
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Événements de la pipeline" />
            <div className="max-h-[30rem] space-y-2 overflow-y-auto p-4">
              {events.length === 0 ? (
                <EmptyState
                  title="En attente d'événements"
                  description="Lancez un run sur cette production pour voir les étapes défiler."
                />
              ) : (
                events.map((event, index) => {
                  const type = typeof event.type === 'string' ? event.type : 'unknown';
                  const meta = EVENT_META[type] ?? { label: type, tone: 'muted' as const };
                  const summary = eventSummary(event);
                  const stepIcon = typeof event.step === 'string' ? STEP_ICONS[event.step] ?? '' : '';
                  return (
                    <div
                      key={`${event.seq}-${index}`}
                      className="rounded-lg border border-border bg-off-black/50 p-3 animate-fade-in"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs text-muted">{eventTime(event)}</span>
                        <Badge tone={meta.tone}>
                          {stepIcon}
                          {meta.label}
                        </Badge>
                        <span className="ml-auto font-mono text-xs text-muted">seq {event.seq}</span>
                      </div>
                      {summary && <p className="mt-1 text-sm text-muted">{summary}</p>}
                    </div>
                  );
                })
              )}
            </div>
          </Card>

          <Card className="mt-6">
            <CardHeader
              title="Demander une révision"
              subtitle="Human-in-the-loop : relance le pipeline avec une cible et un commentaire."
              actions={
                selected && (selected.production.status === 'queued' || selected.production.status === 'running') ? (
                  <Badge tone="amber">Production en cours — révision indisponible</Badge>
                ) : undefined
              }
            />
            <CardBody className="space-y-4">
              <Field
                label="Étape cible"
                htmlFor="revision-step"
                hint="Étape à partir de laquelle relancer la pipeline."
              >
                <Select
                  id="revision-step"
                  value={revisionStep}
                  onChange={(e) => setRevisionStep(e.target.value)}
                >
                  <option value="director">🎬 director</option>
                  <option value="blender">🧊 blender</option>
                  <option value="qa">🔍 qa</option>
                  <option value="audio">🎵 audio</option>
                  <option value="compositing">🎨 compositing</option>
                  <option value="localization">🌍 localization</option>
                </Select>
              </Field>
              <Field
                label="Commentaire"
                htmlFor="revision-comment"
                hint="Instructions précises pour l'ajustement (ex. « plus de pluie, caméra plus basse »)."
              >
                <TextArea
                  id="revision-comment"
                  rows={3}
                  value={revisionComment}
                  onChange={(e) => setRevisionComment(e.target.value)}
                  placeholder="Décrivez ce qui doit changer…"
                />
              </Field>
              <div className="flex items-center gap-3">
                <Button
                  onClick={() => void handleRevision()}
                  disabled={!productionId || revisionBusy || (!selected?.production ? true : selected.production.status === 'queued' || selected.production.status === 'running')}
                >
                  {revisionBusy ? <Spinner className="border-t-black" /> : 'Lancer la révision'}
                </Button>
                {revisionError ? (
                  <p role="alert" className="text-sm text-red-400">
                    {revisionError}
                  </p>
                ) : null}
              </div>
            </CardBody>
          </Card>

          <Card className="mt-6">
            <CardHeader
              title="Timeline & Artefacts"
              subtitle="Visualisez la structure de la production et les fichiers générés."
            />
            <Tabs defaultValue="timeline" className="w-full">
              <TabList className="grid w-full grid-cols-2">
                <TabTrigger value="timeline">📋 Timeline</TabTrigger>
                <TabTrigger value="artifacts">📦 Artefacts</TabTrigger>
              </TabList>

<TabContent value="timeline">
                {timelineLoading ? (
                  <div className="space-y-2 p-4">
                    {[0, 1, 2].map((i) => (
                      <Skeleton key={i} className="h-10 w-full" />
                    ))}
                  </div>
                ) : (timeline ? (
                  <TimelineView
                    timeline={timeline}
                    patchTargets={patchTargets}
                    onPatchTargetChange={(shotId, field, value) =>
                      setPatchTargets((prev) => {
                        const updated = { ...prev };
                        updated[shotId] = { ...updated[shotId], [field]: value };
                        return updated;
                      })}
                    onSubmitPatch={handlePatch}
                    patchBusy={patchBusy}
                  />
                ) : (
                  <EmptyState
                    title="Aucune timeline"
                    description="La timeline sera disponible après les étapes story/storyboard."
                  />
                ))}
              </TabContent>

              <TabContent value="artifacts">
                <CardBody className="space-y-4">
                  {previewUrl ? (
                    <div className="overflow-hidden rounded-lg border border-border bg-black">
                      {previewUrl.isVideo ? (
                        <video src={previewUrl.url} controls className="max-h-96 w-full" />
                      ) : (
                        <img src={previewUrl.url} alt="Aperçu de la production" className="max-h-96 w-full object-contain" />
                      )}
                    </div>
                  ) : null}
                  {artifactsLoading ? (
                    <div className="space-y-2">
                      {[0, 1, 2].map((i) => (
                        <Skeleton key={i} className="h-10 w-full" />
                      ))}
                    </div>
                  ) : null}
                  {!artifactsLoading && artifacts.length === 0 ? (
                    <EmptyState
                      title="Aucun artefact"
                      description="Lancez un run pour que les agents génèrent specs, scripts et rendus."
                    />
                  ) : null}
                  {!artifactsLoading && artifacts.length ? (
                    <ul className="divide-y divide-border rounded-lg border border-border">
                      {artifacts.map((artifact) => {
                        const viewType = artifactViewType(artifact);
                        const canView = viewType !== null;
                        return (
                          <li
                            key={artifact.path}
                            className="flex flex-wrap items-center gap-3 px-4 py-3 transition-colors hover:bg-off-black/50"
                          >
                            <div className="min-w-0 flex-1">
                              <button
                                type="button"
                                onClick={() => canView && setViewingArtifact(artifact)}
                                className={`truncate font-mono text-sm ${canView ? 'text-acid hover:underline cursor-pointer' : 'text-off-white'}`}
                                title={canView ? 'Cliquez pour visualiser' : artifact.path}
                              >
                                {artifact.name}
                              </button>
                              <p className="text-xs text-muted">
                                {artifact.type} · {fmtSize(artifact.size)}
                                {canView && <span className="ml-2 text-acid/60">● cliquable</span>}
                              </p>
                            </div>
                            <Badge tone="muted">v{selected?.production.version ?? '—'}</Badge>
                            {canView ? (
                              <Button
                                variant="ghost"
                                className="px-3 py-1.5 text-xs"
                                onClick={() => setViewingArtifact(artifact)}
                              >
                                Visualiser
                              </Button>
                            ) : null}
                            <Button
                              variant="outline"
                              className="px-3 py-1.5"
                              onClick={() => void handleDownload(artifact)}
                            >
                              Télécharger
                            </Button>
                            <Button
                              variant="danger"
                              className="px-3 py-1.5"
                              disabled={deleteBusy === artifact.path}
                              onClick={() => void handleDeleteArtifact(artifact)}
                            >
                              {deleteBusy === artifact.path ? <Spinner className="border-t-red-300 h-3 w-3" /> : 'Supprimer'}
                            </Button>
                          </li>
                        );
                      })}
                    </ul>
                  ) : null}
                </CardBody>
              </TabContent>
            </Tabs>
          </Card>
        </>
      )}

      {viewingArtifact && productionId && (
        <ArtifactViewer
          artifact={viewingArtifact}
          productionId={productionId}
          onClose={() => setViewingArtifact(null)}
        />
      )}
    </div>
  );
}
