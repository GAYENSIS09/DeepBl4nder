'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

export type ToastKind = 'success' | 'error' | 'info';

interface ToastItem {
  id: number;
  kind: ToastKind;
  message: string;
}

interface NotificationsContextValue {
  notify: (kind: ToastKind, message: string) => void;
}

const NotificationsContext = createContext<NotificationsContextValue | null>(null);

const DURATION: Record<ToastKind, number> = {
  success: 6000,
  error: 8000,
  info: 4000,
};

const STYLE: Record<ToastKind, { border: string; dot: string }> = {
  success: { border: 'border-acid/60', dot: 'bg-acid' },
  error: { border: 'border-red-500/70', dot: 'bg-red-500' },
  info: { border: 'border-muted/60', dot: 'bg-muted' },
};

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const notify = useCallback(
    (kind: ToastKind, message: string) => {
      const id = nextId.current++;
      setToasts((prev) => [...prev, { id, kind, message }]);
      window.setTimeout(() => dismiss(id), DURATION[kind]);
    },
    [dismiss],
  );

  const value = useMemo(() => ({ notify }), [notify]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setToasts([]);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <NotificationsContext.Provider value={value}>
      {children}
      <div
        className="fixed top-4 right-4 z-50 flex w-80 flex-col gap-2"
        role="region"
        aria-label="Notifications"
        aria-live="polite"
      >
        {toasts.map((toast) => {
          const style = STYLE[toast.kind];
          return (
            <div
              key={toast.id}
              role={toast.kind === 'error' ? 'alert' : 'status'}
              className={`card-bg border ${style.border} rounded-lg shadow-lg animate-fade-up p-3`}
            >
              <div className="flex items-start gap-2">
                <span className={`mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full ${style.dot}`} />
                <p className="text-sm text-off-white">{toast.message}</p>
                <button
                  type="button"
                  onClick={() => dismiss(toast.id)}
                  aria-label="Fermer la notification"
                  className="ml-auto text-muted hover:text-off-white transition-colors"
                >
                  ✕
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </NotificationsContext.Provider>
  );
}

export function useNotifications(): NotificationsContextValue {
  const ctx = useContext(NotificationsContext);
  if (!ctx) throw new Error('useNotifications doit être utilisé dans <NotificationsProvider>.');
  return ctx;
}
