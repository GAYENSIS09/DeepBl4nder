'use client';

/**
 * Client SSE pour l'API SaaS DeepBlender.
 *
 * Le navigateur natif `EventSource` ne peut pas envoyer d'en-têtes
 * (Authorization requis), on passe donc par `fetch` + `ReadableStream`.
 *
 * Garanties :
 *  - reconnecte automatiquement avec backoff exponentiel borné ;
 *  - reprend le flux via `?after=<seq>` (équivalent `Last-Event-ID`) ;
 *  - déduplique les événements par `seq` ;
 *  - traite le heartbeat serveur (`event: ping`) ;
 *  - s'arrête proprement (abort + timer) sur `close()` ou un signal externe.
 */

export interface SSEEvent {
  seq: number;
  [key: string]: unknown;
}

export type SSEStatus =
  | { state: 'idle' }
  | { state: 'connecting'; attempt: number }
  | { state: 'connected' }
  | { state: 'reconnecting'; attempt: number; delayMs: number }
  | { state: 'error'; message: string };

export interface SSEHandle {
  close: () => void;
}

export interface ConnectSSEOptions {
  url: string;
  token: string;
  after?: number;
  onEvent: (event: SSEEvent) => void;
  onStatus: (status: SSEStatus) => void;
  onHeartbeat?: () => void;
  signal?: AbortSignal;
  baseBackoffMs?: number;
  maxBackoffMs?: number;
}

const BASE_BACKOFF_MS = 500;
const MAX_BACKOFF_MS = 30000;

export function connectSSE(options: ConnectSSEOptions): SSEHandle {
  const {
    url,
    token,
    after = 0,
    onEvent,
    onStatus,
    onHeartbeat,
    signal,
    baseBackoffMs = BASE_BACKOFF_MS,
    maxBackoffMs = MAX_BACKOFF_MS,
  } = options;

  let closed = false;
  let controller: AbortController | null = null;
  let lastSeq = after;
  let attempt = 0;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;

  const emitStatus = (status: SSEStatus): void => {
    if (!closed) onStatus(status);
  };

  const buildUrl = (): string => {
    const target = new URL(url);
    if (lastSeq > 0) target.searchParams.set('after', String(lastSeq));
    return target.toString();
  };

  const scheduleReconnect = async (): Promise<void> => {
    const delayMs = Math.min(maxBackoffMs, baseBackoffMs * 2 ** Math.max(0, attempt - 1));
    emitStatus({ state: 'reconnecting', attempt, delayMs });
    await new Promise<void>((resolve) => {
      retryTimer = setTimeout(resolve, delayMs);
      if (controller) {
        controller.signal.addEventListener(
          'abort',
          () => {
            if (retryTimer) clearTimeout(retryTimer);
            resolve();
          },
          { once: true },
        );
      }
    });
  };

  async function run(): Promise<void> {
    while (!closed) {
      attempt += 1;
      emitStatus({ state: 'connecting', attempt });

      const abort = new AbortController();
      controller = abort;
      const onExternalAbort = (): void => abort.abort();
      signal?.addEventListener('abort', onExternalAbort, { once: true });

      try {
        const response = await fetch(buildUrl(), {
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: 'text/event-stream',
          },
          signal: abort.signal,
        });
        if (closed) return;

        if (response.status === 401 || response.status === 403) {
          emitStatus({ state: 'error', message: `Authentification refusée (${response.status})` });
          return;
        }
        if (response.status === 404) {
          emitStatus({ state: 'error', message: 'Production introuvable (404)' });
          return;
        }
        if (!response.ok) {
          emitStatus({ state: 'error', message: `Erreur HTTP ${response.status}` });
          return;
        }
        if (!response.body) {
          emitStatus({ state: 'error', message: 'Flux non pris en charge par ce navigateur' });
          return;
        }

        emitStatus({ state: 'connected' });
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        try {
          while (!closed) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split('\n\n');
            buffer = parts.pop() ?? '';
            for (const block of parts) {
              let eventName = '';
              let data: string | undefined;
              for (const line of block.split('\n')) {
                if (line.startsWith('event:')) eventName = line.slice(6).trim();
                else if (line.startsWith('data:')) {
                  const piece = line.slice(5).trimStart();
                  data = data === undefined ? piece : `${data}\n${piece}`;
                }
              }
              if (eventName === 'ping' || eventName === 'heartbeat') {
                onHeartbeat?.();
                continue;
              }
              if (data === undefined || data === '') continue;
              let parsed: unknown;
              try {
                parsed = JSON.parse(data);
              } catch {
                continue;
              }
              if (typeof parsed !== 'object' || parsed === null) continue;
              const record = parsed as Record<string, unknown>;
              const seq = typeof record.seq === 'number' ? record.seq : 0;
              if (seq > 0 && seq <= lastSeq) continue;
              lastSeq = Math.max(lastSeq, seq);
              onEvent({ ...record, seq } as SSEEvent);
            }
          }
        } catch {
          if (closed) return;
          // Erreur de lecture réseau → reconnexion.
        } finally {
          reader.releaseLock();
        }

        if (closed) return;
        if (controller === abort) controller = null;
        await scheduleReconnect();
      } catch {
        if (closed) return;
        if (controller === abort) controller = null;
        await scheduleReconnect();
      } finally {
        signal?.removeEventListener('abort', onExternalAbort);
      }
    }
  }

  function close(): void {
    if (closed) return;
    closed = true;
    if (retryTimer) clearTimeout(retryTimer);
    controller?.abort();
    onStatus({ state: 'idle' });
  }

  void run();
  return { close };
}
