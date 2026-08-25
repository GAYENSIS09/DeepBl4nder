'use client';

/**
 * Visualiseurs d'artefacts : JSON lisible (arbre replié + coloration),
 * code numéroté et lecteurs média redesignés. Aucune dépendance externe.
 */

import { useMemo, useState } from 'react';
import { Button } from '@/components/ui';

/* ------------------------------------------------------------------ */
/* JSON                                                                */
/* ------------------------------------------------------------------ */

type JsonValue = unknown;

/** Chemins de tous les nœuds conteneurs (objets/tableaux non vides). */
function collectContainerPaths(value: JsonValue, prefix = '$', depth = 0, acc: Array<{ path: string; depth: number }> = []): Array<{ path: string; depth: number }> {
  if (Array.isArray(value)) {
    if (value.length > 0) acc.push({ path: prefix, depth });
    value.forEach((item, i) => collectContainerPaths(item, `${prefix}[${i}]`, depth + 1, acc));
  } else if (value !== null && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, JsonValue>);
    if (entries.length > 0) acc.push({ path: prefix, depth });
    entries.forEach(([key, child]) => collectContainerPaths(child, `${prefix}.${key}`, depth + 1, acc));
  }
  return acc;
}

const PRIMITIVES: Record<string, string> = {
  string: 'text-emerald-300',
  number: 'text-amber-300',
  boolean: 'text-violet-300',
};

function PrimitiveValue({ value }: { value: Exclude<JsonValue, object> }) {
  const kind = typeof value;
  const label = kind === 'string' ? `"${value}"` : String(value);
  return (
    <span className={`${PRIMITIVES[kind] ?? 'text-muted'} break-all`}>
      {label}
    </span>
  );
}

function CountBadge({ count, unit }: { count: number; unit: string }) {
  return (
    <span className="ml-1.5 rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-muted">
      {count} {unit}{count !== 1 ? 's' : ''}
    </span>
  );
}

interface TreeNodeProps {
  name: string | null;
  value: JsonValue;
  path: string;
  depth: number;
  expanded: Set<string>;
  toggle: (path: string) => void;
}

function TreeNode({ name, value, path, depth, expanded, toggle }: TreeNodeProps) {
  const isArray = Array.isArray(value);
  const isObject = !isArray && value !== null && typeof value === 'object';
  const isContainer = isArray || isObject;
  const entries: Array<[string, JsonValue]> = isArray
    ? (value as Array<JsonValue>).map((item, i) => [String(i), item])
    : isObject
      ? Object.entries(value as Record<string, JsonValue>)
      : [];
  const isOpen = expanded.has(path);

  const head = name !== null && (
    <span className="mr-1 shrink-0 text-sky-300">
      {isArray ? `[${name}]` : name}
      <span className="text-muted"> :</span>
    </span>
  );

  if (!isContainer) {
    return (
      <div className="flex items-start gap-1 py-px leading-relaxed">
        {head}
        <PrimitiveValue value={value as Exclude<JsonValue, object>} />
      </div>
    );
  }

  return (
    <div style={{ paddingLeft: depth === 0 ? 0 : undefined }}>
      <button
        type="button"
        onClick={() => toggle(path)}
        aria-expanded={isOpen}
        className="group flex w-full items-start gap-1 rounded px-0.5 py-px text-left hover:bg-white/5"
      >
        <span className={`mt-[3px] shrink-0 text-[10px] transition-transform ${isOpen ? 'rotate-90' : ''} text-acid`}>▶</span>
        {head}
        {isOpen ? (
          <span className="text-muted">{isArray ? '[' : '{'}</span>
        ) : (
          <>
            <span className="text-muted">{isArray ? '[ … ]' : '{ … }'}</span>
            <CountBadge count={entries.length} unit={isArray ? 'élément' : 'clé'} />
          </>
        )}
      </button>
      {isOpen ? (
        <div className="ml-3 border-l border-border/70 pl-3">
          {entries.map(([key, child]) => (
            <TreeNode
              key={key}
              name={key}
              value={child}
              path={isArray ? `${path}[${key}]` : `${path}.${key}`}
              depth={depth + 1}
              expanded={expanded}
              toggle={toggle}
            />
          ))}
          <div className="py-px text-muted">{isArray ? ']' : '}'}</div>
        </div>
      ) : null}
    </div>
  );
}

export function JsonViewer({ data, filename }: { data: JsonValue; filename: string }) {
  const containers = useMemo(() => collectContainerPaths(data), [data]);
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(containers.filter((c) => c.depth <= 2).map((c) => c.path)),
  );
  const [copied, setCopied] = useState(false);

  const formatted = useMemo(() => JSON.stringify(data, null, 2), [data]);
  const lineCount = useMemo(() => formatted.split('\n').length, [formatted]);

  const toggle = (path: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });

  const setAll = (open: boolean) =>
    setExpanded(open ? new Set(containers.map((c) => c.path)) : new Set());

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formatted);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard indisponible */
    }
  };

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border border-border bg-off-black/60 px-3 py-2">
        <span className="font-mono text-xs text-acid">{filename}</span>
        <CountBadge count={containers.length} unit="nœud" />
        <span className="hidden text-xs text-muted sm:inline">
          {lineCount} ligne{lineCount !== 1 ? 's' : ''} formatée{lineCount !== 1 ? 's' : ''}
        </span>
        <span className="ml-auto flex flex-wrap items-center gap-1.5">
          <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => setAll(true)}>
            Tout déplier
          </Button>
          <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => setAll(false)}>
            Tout replier
          </Button>
          <Button variant="outline" className="px-2 py-1 text-xs" onClick={() => void handleCopy()}>
            {copied ? 'Copié !' : 'Copier'}
          </Button>
        </span>
      </div>
      <div className="min-h-0 flex-1 overflow-auto rounded-lg border border-border bg-black/50 p-3 font-mono text-xs sm:text-sm">
        <TreeNode
          name={null}
          value={data}
          path="$"
          depth={0}
          expanded={expanded}
          toggle={toggle}
        />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Code / texte                                                        */
/* ------------------------------------------------------------------ */

export function CodeViewer({ content }: { content: string }) {
  const lines = useMemo(() => content.replace(/\n$/, '').split('\n'), [content]);
  return (
    <div className="h-full overflow-auto rounded-lg border border-border bg-black/50 font-mono text-xs sm:text-sm">
      <table className="w-full border-collapse">
        <tbody>
          {lines.map((line, i) => (
            <tr key={i} className="hover:bg-white/5">
              <td className="w-10 select-none border-r border-border/60 px-2 py-px text-right align-top text-[11px] leading-relaxed text-muted/60 sm:w-14">
                {i + 1}
              </td>
              <td className="whitespace-pre-wrap break-words px-3 py-px leading-relaxed text-off-white/90">
                {line || '\u00A0'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Média                                                               */
/* ------------------------------------------------------------------ */

export function VideoPlayer({ url, filename }: { url: string; filename: string }) {
  return (
    <figure className="flex h-full flex-col items-center justify-center gap-3">
      <div className="w-full overflow-hidden rounded-xl border border-border bg-black shadow-[0_0_40px_rgba(170,255,0,0.06)]">
        <video
          src={url}
          controls
          playsInline
          preload="metadata"
          className="aspect-video max-h-[62vh] w-full bg-black"
        />
      </div>
      <figcaption className="max-w-full truncate font-mono text-xs text-muted">
        🎬 {filename}
      </figcaption>
    </figure>
  );
}

export function AudioPlayer({ url, filename }: { url: string; filename: string }) {
  return (
    <div className="flex h-full items-center justify-center p-2 sm:p-6">
      <div className="w-full max-w-md space-y-4 rounded-xl border border-border bg-off-black/80 p-4 sm:p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-acid/10 text-2xl">
            🎵
          </div>
          <div className="min-w-0">
            <p className="truncate font-display font-medium text-off-white">{filename}</p>
            <p className="text-xs text-muted">Piste audio</p>
          </div>
        </div>
        <div
          aria-hidden
          className="flex h-8 items-end justify-between gap-[3px] overflow-hidden rounded-lg bg-black/40 px-2 py-1"
        >
          {[0.35, 0.7, 0.45, 0.9, 0.55, 0.75, 0.3, 0.85, 0.5, 0.65, 0.4, 0.95, 0.6, 0.35, 0.8, 0.5].map(
            (level, i) => (
              <span
                key={i}
                className="w-1 rounded-sm bg-acid/40"
                style={{ height: `${Math.round(level * 100)}%` }}
              />
            ),
          )}
        </div>
        <audio src={url} controls preload="metadata" className="w-full" />
      </div>
    </div>
  );
}

export function ImagePlayer({ url, filename }: { url: string; filename: string }) {
  return (
    <figure className="flex h-full flex-col items-center justify-center gap-3">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={url}
        alt={filename}
        className="max-h-[62vh] max-w-full rounded-xl border border-border object-contain shadow-2xl"
      />
      <figcaption className="max-w-full truncate font-mono text-xs text-muted">
        🖼 {filename}
      </figcaption>
    </figure>
  );
}
