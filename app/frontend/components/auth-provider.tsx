"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { User } from "@/types";
import { api, ApiError, errorMessage } from "@/lib/api";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  error: string;
  refresh: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}
const AuthContext = createContext<AuthContextValue | null>(null);
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try { setUser(await api.me()); }
    catch (error) { setUser(null); if (!(error instanceof ApiError && error.status === 401)) setError(errorMessage(error)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => {
    let active = true;
    api.me().then(value => { if (active) setUser(value); })
      .catch(error => { if (active && !(error instanceof ApiError && error.status === 401)) setError(errorMessage(error)); })
      .finally(() => { if (active) setLoading(false); });
    const expired = () => setUser(null);
    window.addEventListener("auladata:unauthorized", expired);
    return () => { active = false; window.removeEventListener("auladata:unauthorized", expired); };
  }, []);
  async function login(email: string, password: string) {
    await api.login(email, password);
    setUser(await api.me());
    setError("");
  }
  async function logout() { await api.logout(); setUser(null); }
  return <AuthContext.Provider value={{ user, loading, error, refresh, login, logout }}>{children}</AuthContext.Provider>;
}
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("AuthProvider no está disponible.");
  return context;
}
