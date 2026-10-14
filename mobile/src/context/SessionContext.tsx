import * as SecureStore from "expo-secure-store";
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { ApiClient, ApiError, createApiClient } from "../lib/api";
import type { Language, User, UserProfile } from "../types";

const TOKEN_KEY = "diet-journal.session-token";
export type SessionStatus = "loading" | "signedOut" | "signedIn" | "unavailable";

type LoginResponse = {
  access_token: string;
  token_type: "Bearer";
  expires_in: number;
  expires_at: string;
  user: User;
};

type SessionContextValue = {
  status: SessionStatus;
  user: User | null;
  language: Language;
  setLanguage: (language: Language) => void;
  api: ApiClient;
  error: string | null;
  login: (loginId: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  retrySession: () => Promise<void>;
};

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: React.PropsWithChildren) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [language, setLanguage] = useState<Language>("zh");
  const [status, setStatus] = useState<SessionStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  const clearSession = useCallback(async () => {
    setToken(null);
    setUser(null);
    setStatus("signedOut");
    setError(null);
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  }, []);

  const api = useMemo(() => createApiClient(() => token, clearSession), [clearSession, token]);

  const setSessionToken = useCallback((value: string | null) => {
    setToken(value);
  }, []);

  const verifyStoredSession = useCallback(() => {
    return SecureStore.getItemAsync(TOKEN_KEY).then((storedToken) => {
      if (!storedToken) {
        setSessionToken(null);
        setUser(null);
        setStatus("signedOut");
        return;
      }
      setSessionToken(storedToken);
      const client = createApiClient(() => storedToken, clearSession);
      return client.json<User>("/me").then((current) => {
        setUser(current);
        setStatus("signedIn");
        void client.json<{ profile: UserProfile }>("/profile")
          .then((result) => setLanguage(result.profile.language ?? "zh"))
          .catch(() => undefined);
      }).catch((cause: unknown) => {
        if (cause instanceof ApiError && cause.status === 401) {
          return clearSession();
        }
        setStatus("unavailable");
        setError(cause instanceof Error ? cause.message : "暂时无法连接饮食服务。");
      });
    }).catch(() => {
      setStatus("unavailable");
      setError("无法读取设备安全存储，请稍后重试。");
    });
  }, [clearSession, setSessionToken]);

  const retrySession = useCallback(async () => {
    setStatus("loading");
    setError(null);
    await verifyStoredSession();
  }, [verifyStoredSession]);

  useEffect(() => {
    void verifyStoredSession();
  }, [verifyStoredSession]);

  const login = useCallback(async (loginId: string, password: string) => {
    setError(null);
    const result = await api.json<LoginResponse>(
      "/auth/mobile/login",
      {
        method: "POST",
        body: JSON.stringify({ login_id: loginId, password }),
        authenticated: false,
      },
    );
    await SecureStore.setItemAsync(TOKEN_KEY, result.access_token);
    setSessionToken(result.access_token);
    setUser(result.user);
    setStatus("signedIn");
    const client = createApiClient(() => result.access_token, clearSession);
    void client.json<{ profile: UserProfile }>("/profile")
      .then((profileResult) => setLanguage(profileResult.profile.language ?? "zh"))
      .catch(() => undefined);
  }, [api, clearSession, setSessionToken]);

  const logout = useCallback(async () => {
    try {
      if (token) {
        await api.json("/auth/logout", { method: "POST", body: "{}" });
      }
    } catch {
      // Always remove the local bearer token, even when the server is unreachable.
    } finally {
      await clearSession();
    }
  }, [api, clearSession, token]);

  return (
    <SessionContext.Provider value={{ status, user, language, setLanguage, api, error, login, logout, retrySession }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used within SessionProvider");
  return value;
}
