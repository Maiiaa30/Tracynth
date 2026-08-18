import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getSession, login as requestLogin, logout as requestLogout } from '../lib/api';
import type { User } from '../types/api';

interface AuthValue {
  user: User | null;
  loading: boolean;
  error: string | null;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const session = await getSession();
      setUser(session.authenticated ? (session.user ?? null) : null);
    } catch (reason) {
      setUser(null);
      setError(reason instanceof Error ? reason.message : 'Unable to check the session.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signIn = useCallback(async (username: string, password: string) => {
    setUser(await requestLogin(username, password));
  }, []);

  const signOut = useCallback(async () => {
    await requestLogout();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, error, signIn, signOut, refresh }),
    [user, loading, error, signIn, signOut, refresh],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used within AuthProvider');
  return value;
}
