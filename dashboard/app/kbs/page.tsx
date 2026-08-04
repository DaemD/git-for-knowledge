"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import {
  apiGet,
  apiPost,
  type KnowledgeBase,
  type Me,
} from "@/lib/api";

type ListResponse = {
  username: string;
  knowledge_bases: KnowledgeBase[];
};

function slugifyKbId(name: string): string {
  const slug = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
  if (!slug) return "";
  if (/^[a-z0-9]/.test(slug)) return slug;
  return `kb-${slug}`.slice(0, 64);
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function KnowledgeBasesPage() {
  const auth = useAuth();
  const [me, setMe] = useState<Me | null>(null);
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    if (!auth.token) return;
    setLoading(true);
    setError(null);
    try {
      const [meRes, listRes] = await Promise.all([
        apiGet<Me>("/api/v1/me", auth.token),
        apiGet<ListResponse>("/api/v1/kbs", auth.token),
      ]);
      setMe(meRes);
      setKbs(listRes.knowledge_bases);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [auth.token]);

  useEffect(() => {
    if (!auth.ready) return;
    if (!auth.isAuthenticated) {
      setLoading(false);
      return;
    }
    void load();
  }, [auth.isAuthenticated, auth.ready, load]);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    if (!auth.token) return;
    const label = name.trim();
    const kbId = slugifyKbId(label);
    if (!kbId) {
      setError("Enter a name for the knowledge base");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      await apiPost("/api/v1/kbs", auth.token, {
        kb_id: kbId,
        name: label,
      });
      setName("");
      setShowCreate(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setCreating(false);
    }
  }

  if (!auth.ready) {
    return <p className="empty">Loading…</p>;
  }

  if (!auth.isAuthenticated) {
    return (
      <section className="panel login-card">
        <h1>Sign in to grphly</h1>
        <p className="page-sub" style={{ marginBottom: 16 }}>
          Use your Google account to manage knowledge bases.
        </p>
        {auth.error ? <p className="error">{auth.error}</p> : null}
        <button type="button" className="btn btn-primary" onClick={auth.login}>
          Continue with Google
        </button>
      </section>
    );
  }

  if (!auth.token) {
    return <p className="empty">Preparing session…</p>;
  }

  const suggestedId = slugifyKbId(name);

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Knowledge bases</h1>
          <p className="page-sub">
            {kbs.length} total
            {me ? ` · Plan ${me.plan_status}` : ""}
          </p>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setShowCreate((open) => !open)}
        >
          {showCreate ? "Cancel" : "New knowledge base"}
        </button>
      </div>

      {error ? <p className="error">{error}</p> : null}

      {showCreate ? (
        <section className="panel" style={{ marginBottom: 16 }}>
          <h2 className="panel-title">Create knowledge base</h2>
          <form className="row" onSubmit={onCreate}>
            <div className="field" style={{ minWidth: "min(100%, 280px)", flex: 1 }}>
              <label htmlFor="name">Name</label>
              <input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Acme research"
                required
                autoFocus
              />
              {suggestedId ? (
                <span className="meta mono">ID will be {suggestedId}</span>
              ) : null}
            </div>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={creating || !suggestedId}
              style={{ alignSelf: "end" }}
            >
              {creating ? "Creating…" : "Create"}
            </button>
          </form>
        </section>
      ) : null}

      {loading ? <p className="empty">Loading…</p> : null}

      {!loading && kbs.length === 0 ? (
        <div className="flash">
          <p className="empty">
            No knowledge bases yet. Create one to get started.
          </p>
        </div>
      ) : null}

      {!loading && kbs.length > 0 ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>ID</th>
                <th>Role</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {kbs.map((kb) => (
                <tr key={kb.kb_id}>
                  <td>
                    <Link href={`/kbs/${kb.kb_id}`} className="kb-name">
                      {kb.name}
                    </Link>
                    {kb.shared && kb.owner_email ? (
                      <div className="meta">Owner {kb.owner_email}</div>
                    ) : null}
                  </td>
                  <td>
                    <code className="mono">{kb.kb_id}</code>
                  </td>
                  <td>
                    <span className="pill">{kb.role}</span>
                  </td>
                  <td className="meta">{formatDate(kb.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </>
  );
}
