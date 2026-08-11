'use client';

import { useCallback, useEffect, useState } from 'react';

import { API_URL } from '@/lib/config';
import { connectSSE, type SSEEvent, type SSEStatus } from '@/lib/sse';

export interface ProductionStreamState {
  events: SSEEvent[];
  status: SSEStatus;
  lastHeartbeatAt: number | null;
  reconnect: () => void;
}

export function useProductionStream(
  productionId: string | null,
  token: string | null,
): ProductionStreamState {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [status, setStatus] = useState<SSEStatus>({ state: 'idle' });
  const [lastHeartbeatAt, setLastHeartbeatAt] = useState<number | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (!productionId || !token) {
      setEvents([]);
      setStatus({ state: 'idle' });
      return;
    }
    setEvents([]);
    setLastHeartbeatAt(null);
    const endpoint = `${API_URL}/api/productions/${encodeURIComponent(productionId)}/events`;
    const handle = connectSSE({
      url: endpoint,
      token,
      onEvent: (event) => setEvents((prev) => [event, ...prev].slice(0, 300)),
      onStatus: setStatus,
      onHeartbeat: () => setLastHeartbeatAt(Date.now()),
    });
    return () => {
      handle.close();
    };
  }, [productionId, token, nonce]);

  const reconnect = useCallback(() => {
    setNonce((n) => n + 1);
  }, []);

  return { events, status, lastHeartbeatAt, reconnect };
}
