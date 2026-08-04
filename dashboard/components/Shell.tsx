"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { authDisabled } from "@/lib/api";

export function Shell({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const pathname = usePathname();
  const onKbs = pathname === "/kbs" || pathname?.startsWith("/kbs/");

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-left">
          <Link href="/kbs" className="brand">
            grphly
          </Link>
          {auth.isAuthenticated ? (
            <Link
              href="/kbs"
              className="nav-link"
              aria-current={onKbs ? "page" : undefined}
            >
              Knowledge bases
            </Link>
          ) : null}
        </div>
        <div className="topbar-meta">
          {auth.ready && auth.isAuthenticated ? (
            <>
              <span>{auth.email || auth.name || "Signed in"}</span>
              {authDisabled() ? <span className="pill">dev</span> : null}
              {!authDisabled() ? (
                <button type="button" className="btn btn-sm" onClick={auth.logout}>
                  Sign out
                </button>
              ) : null}
            </>
          ) : (
            <span>Dashboard</span>
          )}
        </div>
      </header>
      <main className="main">{children}</main>
    </div>
  );
}
