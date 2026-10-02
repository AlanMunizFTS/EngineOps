import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import {
  AUTHENTICATION_EXPIRED_EVENT,
  getCurrentUser,
  type UserResponse,
} from "../api/client";

const TOKEN_STORAGE_KEY = "engineops_token";

interface AuthContextValue {
  token: string | null;
  user: UserResponse | null;
  isLoading: boolean;
  sessionExpired: boolean;
  setSession: (token: string, user: UserResponse) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_STORAGE_KEY),
  );
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);

  useEffect(() => {
    function handleAuthenticationExpired() {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      setToken(null);
      setUser(null);
      setSessionExpired(true);
    }

    window.addEventListener(AUTHENTICATION_EXPIRED_EVENT, handleAuthenticationExpired);
    return () => {
      window.removeEventListener(AUTHENTICATION_EXPIRED_EVENT, handleAuthenticationExpired);
    };
  }, []);

  useEffect(() => {
    if (!token) {
      setIsLoading(false);
      return;
    }
    getCurrentUser(token)
      .then(setUser)
      .catch(() => {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        setToken(null);
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, [token]);

  function setSession(nextToken: string, nextUser: UserResponse) {
    localStorage.setItem(TOKEN_STORAGE_KEY, nextToken);
    setToken(nextToken);
    setUser(nextUser);
    setSessionExpired(false);
  }

  function logout() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
    setSessionExpired(false);
  }

  return (
    <AuthContext.Provider
      value={{ token, user, isLoading, sessionExpired, setSession, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
