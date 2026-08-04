"use client";

import { Auth0Provider, useAuth0 } from "@auth0/auth0-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { authDisabled, devSubject, devToken } from "@/lib/api";

type AuthContextValue = {
  ready: boolean;
  isAuthenticated: boolean;
  token: string | null;
  email: string | null;
  name: string | null;
  login: () => void;
  logout: () => void;
  error: string | null;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function DevAuthProvider({ children }: { children: ReactNode }) {
  const subject = devSubject();
  const value = useMemo<AuthContextValue>(
    () => ({
      ready: true,
      isAuthenticated: true,
      token: devToken(),
      email: `${subject}@local.dev`,
      name: "Dev user",
      login: () => undefined,
      logout: () => undefined,
      error: null,
    }),
    [subject],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function Auth0Session({
  children,
  audience,
}: {
  children: ReactNode;
  audience?: string;
}) {
  const {
    isAuthenticated,
    isLoading,
    loginWithRedirect,
    logout,
    getAccessTokenSilently,
    user,
    error,
  } = useAuth0();
  const [token, setToken] = useState<string | null>(null);
  const [loginError, setLoginError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!isAuthenticated) {
      setToken(null);
      return;
    }
    void getAccessTokenSilently({
      authorizationParams: audience ? { audience } : undefined,
    })
      .then((value) => {
        if (!cancelled) setToken(value);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setToken(null);
          setLoginError(
            err instanceof Error ? err.message : "Failed to get access token",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [audience, getAccessTokenSilently, isAuthenticated]);

  const login = useCallback(() => {
    setLoginError(null);
    void loginWithRedirect({
      authorizationParams: {
        redirect_uri: window.location.origin,
        audience,
        connection: "google-oauth2",
      },
    }).catch((err: unknown) => {
      const message =
        err instanceof Error ? err.message : "Auth0 login redirect failed";
      setLoginError(message);
      console.error("Auth0 login failed", err);
    });
  }, [audience, loginWithRedirect]);

  const value = useMemo<AuthContextValue>(
    () => ({
      ready: !isLoading,
      isAuthenticated,
      token,
      email: user?.email ?? null,
      name: user?.name ?? null,
      login,
      logout: () =>
        logout({ logoutParams: { returnTo: window.location.origin } }),
      error: loginError || error?.message || null,
    }),
    [
      error?.message,
      isAuthenticated,
      isLoading,
      login,
      loginError,
      logout,
      token,
      user?.email,
      user?.name,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function Auth0BrowserProvider({ children }: { children: ReactNode }) {
  const domain = (process.env.NEXT_PUBLIC_AUTH0_DOMAIN || "")
    .trim()
    .replace(/^https?:\/\//, "")
    .replace(/\/$/, "");
  const clientId = (process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID || "").trim();
  const audience = (process.env.NEXT_PUBLIC_AUTH0_AUDIENCE || "").trim() || undefined;

  if (!domain || !clientId) {
    const value: AuthContextValue = {
      ready: true,
      isAuthenticated: false,
      token: null,
      email: null,
      name: null,
      login: () => {
        window.alert(
          "Auth0 env vars were not baked into this build. Redeploy dashboard after setting NEXT_PUBLIC_AUTH0_DOMAIN and NEXT_PUBLIC_AUTH0_CLIENT_ID.",
        );
      },
      logout: () => undefined,
      error:
        "Set NEXT_PUBLIC_AUTH0_DOMAIN and NEXT_PUBLIC_AUTH0_CLIENT_ID, then redeploy the dashboard.",
    };
    return (
      <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
    );
  }

  return (
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience,
      }}
      cacheLocation="localstorage"
      useRefreshTokens
    >
      <Auth0Session audience={audience}>{children}</Auth0Session>
    </Auth0Provider>
  );
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (authDisabled()) {
    return <DevAuthProvider>{children}</DevAuthProvider>;
  }

  // Auth0 SDK must only run in the browser (needs window + correct redirect).
  if (!mounted) {
    return <p className="empty">Loading…</p>;
  }

  return <Auth0BrowserProvider>{children}</Auth0BrowserProvider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
