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
        <h1>grphly</h1>
        <p className="lede">
          Sign in to view and manage your knowledge bases.
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
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div>
          <h1>Knowledge bases</h1>
          <p className="lede" style={{ marginBottom: "1rem" }}>
            All knowledge bases linked to your account load automatically.
            {me ? (
              <>
                {" "}
                Plan: <span className="mono">{me.plan_status}</span>
              </>
            ) : null}
          </p>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          style={{ alignSelf: "start" }}
          onClick={() => setShowCreate((open) => !open)}
        >
          {showCreate ? "Cancel" : "New knowledge base"}
        </button>
      </div>

      {error ? <p className="error">{error}</p> : null}

      {showCreate ? (
        <section className="panel" style={{ marginBottom: "1.25rem" }}>
          <h2>New knowledge base</h2>
          <form className="row" onSubmit={onCreate}>
            <div className="field" style={{ minWidth: "min(100%, 22rem)" }}>
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
                <span className="meta mono">id: {suggestedId}</span>
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

      <section>
        {loading ? <p className="empty">Loading your knowledge bases…</p> : null}
        {!loading && kbs.length === 0 ? (
          <p className="empty">
            No knowledge bases yet. Create one, or push from an AI tool after{" "}
            <span className="mono">kb create</span>.
          </p>
        ) : null}
        <div className="kb-grid">
          {kbs.map((kb) => (
            <Link key={kb.kb_id} href={`/kbs/${kb.kb_id}`} className="kb-card">
              <h3>{kb.name}</h3>
              <p className="meta mono">{kb.kb_id}</p>
              <p className="meta" style={{ marginTop: "0.55rem" }}>
                <span className="pill">{kb.role}</span>
                {kb.shared && kb.owner_email ? (
                  <> · owner {kb.owner_email}</>
                ) : null}
              </p>
            </Link>
          ))}
        </div>
      </section>
    </>
  );
}
