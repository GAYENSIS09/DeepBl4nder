'use client';

import { useEffect, useState, useRef } from 'react';

interface EventData {
  type: string;
  [key: string]: unknown;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function EventStream() {
  const [events, setEvents] = useState<EventData[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource(`${API_URL}/events`);
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnected(true);
      setError(null);
    };

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setEvents((prev) => [data, ...prev].slice(0, 100));
      } catch {
        // Ignore parse errors
      }
    };

    es.onerror = () => {
      setConnected(false);
      setError('Connexion perdue. Reconnexion…');
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, []);

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-3">
        <span
          className={`w-3 h-3 rounded-full ${
            connected ? 'bg-green-500' : 'bg-red-500 animate-pulse'
          }`}
        />
        <span className="text-sm">
          {connected ? 'Connecté (SSE)' : 'Déconnecté'}
        </span>
        {error && <span className="text-red-400 text-sm">{error}</span>}
      </div>

      <div className="h-96 bg-gray-900 border border-gray-700 rounded-lg overflow-auto p-3 font-mono text-xs">
        {events.length === 0 ? (
          <div className="text-gray-500 text-center py-8">En attente d'événements…</div>
        ) : (
          events.map((event, i) => (
            <div
              key={i}
              className="border-b border-gray-800 pb-1 last:border-0"
            >
              <span className="text-gray-500">[{new Date().toLocaleTimeString()}]</span>{' '}
              <span className="text-blue-400">{event.type}</span>{' '}
              <span className="text-gray-400">
                {JSON.stringify(event, null, 0).slice(0, 200)}
              </span>
            </div>
          ))
        )}
      </div>

      <details className="border border-gray-700 rounded-lg bg-gray-800/50">
        <summary className="p-3 cursor-pointer font-medium">Types d'événements</summary>
        <div className="px-3 pb-3 text-sm text-gray-400 space-y-1">
          <div><strong>run_started / run_completed / run_blocked</strong> — cycle de vie du run</div>
          <div><strong>step_started / step_completed / step_failed</strong> — transitions d'étapes</div>
          <div><strong>approval_requested / approval_granted / approval_rejected</strong> — human-in-the-loop</div>
          <div><strong>revision_requested</strong> — RevisionSpec créée (target_step, revision)</div>
          <div><strong>cost_recorded</strong> — coût par étape (director, blender, qa, audio, etc.)</div>
          <div><strong>budget_alert</strong> — dépassement budget (temps réel < 30s)</div>
        </div>
      </details>
    </section>
  );
}