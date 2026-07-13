"use client";

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import Cookies from "js-cookie";
import { api } from "@/lib/api";

interface User {
  id: string;
  email: string;
  name: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const savedToken = Cookies.get("auth_token");
    if (!savedToken) {
      setIsLoading(false);
      return;
    }

    setToken(savedToken);
    api.auth
      .me(savedToken)
      .then((u) => {
        if (u && u.id && u.email) {
          setUser(u);
        } else {
          Cookies.remove("auth_token");
          setToken(null);
        }
      })
      .catch(() => {
        Cookies.remove("auth_token");
        setToken(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.auth.login(email, password);
    Cookies.set("auth_token", res.access_token, { expires: 7, sameSite: "lax" });
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const register = useCallback(async (email: string, name: string, password: string) => {
    const res = await api.auth.register(email, name, password);
    Cookies.set("auth_token", res.access_token, { expires: 7, sameSite: "lax" });
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const logout = useCallback(() => {
    Cookies.remove("auth_token");
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
