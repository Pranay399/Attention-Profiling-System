/**
 * Auth context — manages user session state.
 *
 * Provides login/logout/register functions and the current user
 * to all components via React context.
 */

'use client';

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { auth as authApi, setAuthToken, getAuthToken, User, ApiError } from '@/lib/api';

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string, role?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
    error: null,
  });

  // Check for existing token on mount
  useEffect(() => {
    const token = getAuthToken();
    if (token) {
      authApi.me()
        .then((user) => setState({ user, loading: false, error: null }))
        .catch(() => {
          setAuthToken(null);
          setState({ user: null, loading: false, error: null });
        });
    } else {
      setState({ user: null, loading: false, error: null });
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setState((prev) => ({ ...prev, error: null, loading: true }));
    try {
      const { access_token } = await authApi.login({ email, password });
      setAuthToken(access_token);
      const user = await authApi.me();
      setState({ user, loading: false, error: null });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Login failed';
      setState((prev) => ({ ...prev, loading: false, error: message }));
      throw err;
    }
  }, []);

  const register = useCallback(async (email: string, password: string, fullName: string, role = 'teacher') => {
    setState((prev) => ({ ...prev, error: null, loading: true }));
    try {
      await authApi.register({ email, password, full_name: fullName, role });
      // Auto-login after registration
      const { access_token } = await authApi.login({ email, password });
      setAuthToken(access_token);
      const user = await authApi.me();
      setState({ user, loading: false, error: null });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Registration failed';
      setState((prev) => ({ ...prev, loading: false, error: message }));
      throw err;
    }
  }, []);

  const logout = useCallback(() => {
    setAuthToken(null);
    setState({ user: null, loading: false, error: null });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
