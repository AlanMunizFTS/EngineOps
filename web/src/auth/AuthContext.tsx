import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import {
  AUTHENTICATION_EXPIRED_EVENT,
  getCurrentUser,
  type UserResponse,
} from "../api/client";
import { getTokenExpirationTime, isTokenExpired } from "./token";

const TOKEN_STORAGE_KEY = "engineops_token";
const MAX_TIMEOUT_MS = 2_147_483_647;

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
      setIsLoading(false);
      setSessionExpired(true);
    }

    window.addEventListener(AUTHENTICATION_EXPIRED_EVENT, handleAuthenticationExpired);
    return () => {
      window.removeEventListener(AUTHENTICATION_EXPIRED_EVENT, handleAuthenticationExpired);
    };
  }, []);

  useEffect(() => {
    if (!token) return;

    const activeToken = token;
    let expirationTimer: number | undefined;

    function checkExpirationAndSchedule() {
      if (expirationTimer !== undefined) window.clearTimeout(expirationTimer);

      if (isTokenExpired(activeToken)) {
        window.dispatchEvent(new Event(AUTHENTICATION_EXPIRED_EVENT));
        return;
      }

      const expirationTime = getTokenExpirationTime(activeToken);
      if (expirationTime === null) return;

      expirationTimer = window.setTimeout(
        checkExpirationAndSchedule,
        Math.min(expirationTime - Date.now(), MAX_TIMEOUT_MS),
      );
    }

    function handleVisibilityChange() {
      if (document.visibilityState === "visible") checkExpirationAndSchedule();
    }

    checkExpirationAndSchedule();
    window.addEventListener("focus", checkExpirationAndSchedule);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      if (expirationTimer !== undefined) window.clearTimeout(expirationTimer);
      window.removeEventListener("focus", checkExpirationAndSchedule);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [token]);

  useEffect(() => {
    if (!token) {
      setIsLoading(false);
      return;
    }

    if (isTokenExpired(token)) {
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    getCurrentUser(token)
      .then((nextUser) => {
        if (!cancelled) setUser(nextUser);
      })
      .catch(() => {
        if (cancelled) return;
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        setToken(null);
        setUser(null);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
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
