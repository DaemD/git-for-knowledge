"use client";

import Link from "next/link";
import { useAuth } from "@/components/AuthProvider";
import { authDisabled } from "@/lib/api";

export function Shell({ children }: { children: React.ReactNode }) {
  const auth = useAuth();

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link href="/kbs" className="brand">
          grphly
        </Link>
        <div className="topbar-meta">
          {auth.ready && auth.isAuthenticated ? (
            <>
              <span>{auth.email || auth.name || "signed in"}</span>
              {authDisabled() ? (
                <span className="pill">dev auth</span>
              ) : (
                <button type="button" className="btn" onClick={auth.logout}>
                  Sign out
                </button>
              )}
            </>
          ) : (
            <span>knowledge dashboard</span>
          )}
        </div>
      </header>
      <main className="main">{children}</main>
    </div>
  );
}
