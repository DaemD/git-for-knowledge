"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { apiGet, apiPost, type KbDetail, type Me } from "@/lib/api";

type Tab = "recent" | "members" | "connect" | "graph";

export default function KnowledgeBaseDetailPage() {
  const params = useParams<{ kbId: string }>();
  const kbId = decodeURIComponent(params.kbId);
  const auth = useAuth();
  const [tab, setTab] = useState<Tab>("recent");
  const [detail, setDetail] = useState<KbDetail | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("write");
  const [inviting, setInviting] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    if (!auth.token) return;
    setLoading(true);
    setError(null);
    try {
      const [detailRes, meRes] = await Promise.all([
        apiGet<KbDetail>(`/api/v1/kbs/${encodeURIComponent(kbId)}`, auth.token),
        apiGet<Me>("/api/v1/me", auth.token),
      ]);
      setDetail(detailRes);
      setMe(meRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load KB");
    } finally {
      setLoading(false);
    }
  }, [auth.token, kbId]);

  useEffect(() => {
    if (!auth.ready || !auth.isAuthenticated || !auth.token) return;
    void load();
  }, [auth.isAuthenticated, auth.ready, auth.token, load]);

  const cursorSnippet = useMemo(() => {
    if (!me) return "";
    const clientId = me.oauth_client_id || "YOUR_AUTH0_CLIENT_ID";
    return `{
  "mcpServers": {
    "grphly": {
      "type": "http",
      "url": "${me.mcp_url}",
      "auth": {
        "CLIENT_ID": "${clientId}"
      }
    }
  }
}`;
  }, [me]);

  async function onInvite(event: FormEvent) {
    event.preventDefault();
    if (!auth.token || !detail) return;
    if (detail.me?.role !== "owner") {
      setError("Only the owner can invite");
      return;
    }
    setInviting(true);
    setError(null);
    try {
      await apiPost(
        `/api/v1/kbs/${encodeURIComponent(kbId)}/invites`,
        auth.token,
        { email: inviteEmail.trim(), role: inviteRole },
      );
      setInviteEmail("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invite failed");
    } finally {
      setInviting(false);
    }
  }

  async function copySnippet() {
    try {
      await navigator.clipboard.writeText(cursorSnippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  if (!auth.ready) return <p className="empty">Loading…</p>;
  if (!auth.isAuthenticated) {
    return (
      <section className="panel login-card">
        <h1>Sign in required</h1>
        <button type="button" className="btn btn-primary" onClick={auth.login}>
          Continue with Google
        </button>
      </section>
    );
  }

  if (loading) return <p className="empty">Loading knowledge base…</p>;
  if (error && !detail) {
    return (
      <>
        <Link href="/kbs" className="meta">
          ← all knowledge bases
        </Link>
        <p className="error">{error}</p>
      </>
    );
  }
  if (!detail) return null;

  const kb = detail.knowledge_base;

  return (
    <>
      <Link href="/kbs" className="meta">
        ← all knowledge bases
      </Link>
      <h1 style={{ marginTop: "0.85rem" }}>{kb.name}</h1>
      <p className="lede">
        <span className="mono">{kb.kb_id}</span>
        {" · "}
        <span className="pill">{kb.role}</span>
        {kb.shared && kb.owner_email ? <> · owner {kb.owner_email}</> : null}
      </p>

      <div className="stat-row">
        <div className="stat">
          <span className="meta">Pushes</span>
          <strong>{detail.push_count}</strong>
        </div>
        <div className="stat">
          <span className="meta">Members</span>
          <strong>{detail.members.filter((m) => m.status === "active").length}</strong>
        </div>
        <div className="stat">
          <span className="meta">Pending invites</span>
          <strong>{detail.members.filter((m) => m.status === "pending").length}</strong>
        </div>
      </div>

      <div className="tabs" role="tablist">
        {(
          [
            ["recent", "Recent"],
            ["members", "Members"],
            ["connect", "Connect"],
            ["graph", "Graph"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className="tab"
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {error ? <p className="error">{error}</p> : null}

      {tab === "recent" ? (
        <section className="panel">
          <h2>Recent additions</h2>
          {detail.recent_additions.length === 0 ? (
            <p className="empty">
              Nothing pushed yet. From an AI tool: kb push …
            </p>
          ) : (
            <div className="list">
              {detail.recent_additions.map((item, index) => (
                <article
                  key={`${item.memory_id || item.accepted_at}-${index}`}
                  className="list-item"
                >
                  <p className="meta">
                    {item.accepted_at}
                    {item.writer_email ? ` · ${item.writer_email}` : ""}
                    {item.client_id ? ` · ${item.client_id}` : ""}
                    {" · "}
                    <span className="pill">{item.status}</span>
                  </p>
                  <p className="preview">{item.preview}</p>
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}

      {tab === "members" ? (
        <section className="panel">
          <h2>Members</h2>
          <div className="list">
            {detail.members.map((member) => (
              <div key={`${member.email}-${member.status}`} className="list-item">
                <p className="meta">
                  {member.email} · <span className="pill">{member.role}</span>{" "}
                  · <span className="pill">{member.status}</span>
                </p>
              </div>
            ))}
          </div>
          {detail.me?.role === "owner" ? (
            <form className="row" style={{ marginTop: "1.25rem" }} onSubmit={onInvite}>
              <div className="field">
                <label htmlFor="invite_email">invite email</label>
                <input
                  id="invite_email"
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="invite_role">role</label>
                <select
                  id="invite_role"
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                >
                  <option value="write">write</option>
                  <option value="read">read</option>
                </select>
              </div>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={inviting}
                style={{ alignSelf: "end" }}
              >
                {inviting ? "Inviting…" : "Invite"}
              </button>
            </form>
          ) : (
            <p className="empty" style={{ marginTop: "1rem" }}>
              Only the owner can invite collaborators.
            </p>
          )}
        </section>
      ) : null}

      {tab === "connect" ? (
        <section className="panel">
          <h2>Connect an AI tool</h2>
          <p className="meta" style={{ marginBottom: "0.85rem" }}>
            Same knowledge base across assistants. MCP URL:{" "}
            <span className="mono">{me?.mcp_url}</span>
          </p>
          <div className="row" style={{ marginBottom: "0.65rem" }}>
            <button type="button" className="btn" onClick={copySnippet}>
              {copied ? "Copied" : "Copy Cursor snippet"}
            </button>
          </div>
          <pre className="snippet">{cursorSnippet}</pre>
        </section>
      ) : null}

      {tab === "graph" ? (
        <section className="panel">
          <h2>Graph explorer</h2>
          <div className="graph-placeholder">
            Neo4j Visualization Library view coming next
            <br />
            <span className="meta">
              scoped to this knowledge base · color filters · provenance
            </span>
          </div>
        </section>
      ) : null}
    </>
  );
}
