'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { api, type UserOut } from '@/lib/api';
import { clearAuth, getToken, saveAuth } from '@/lib/auth';

interface AuthContextValue {
  token: string | null;
  user: UserOut | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserOut | null>(null);
  const [ready, setReady] = useState(false);

  const refreshUser = useCallback(async () => {
    try {
      const me = await api.me();
      setUser(me.user);
    } catch {
      // Session expirée : on repart sans utilisateur.
    }
  }, []);

  useEffect(() => {
    const stored = getToken();
    if (!stored) {
      setReady(true);
      return;
    }
    setToken(stored);
    api
      .me()
      .then((me) => setUser(me.user))
      .catch(() => clearAuth())
      .finally(() => setReady(true));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await api.login({ email, password });
    saveAuth(result.access_token, email);
    setToken(result.access_token);
    const me = await api.me();
    setUser(me.user);
  }, []);

  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    const result = await api.register({ email, password, full_name: fullName });
    saveAuth(result.access_token, email);
    setToken(result.access_token);
    const me = await api.me();
    setUser(me.user);
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ token, user, ready, login, register, logout, refreshUser }),
    [token, user, ready, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth doit être utilisé dans <AuthProvider>.');
  return ctx;
}
