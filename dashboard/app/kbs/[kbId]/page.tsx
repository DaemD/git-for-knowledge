"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { GraphExplorer } from "@/components/GraphExplorer";
import { apiGet, apiPost, type KbDetail, type Me } from "@/lib/api";

type Tab = "recent" | "members" | "connect" | "graph";

function formatWhen(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

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

  if (loading) return <p className="empty">Loading…</p>;
  if (error && !detail) {
    return (
      <>
        <div className="breadcrumb">
          <Link href="/kbs">Knowledge bases</Link>
          <span>/</span>
          <span>{kbId}</span>
        </div>
        <p className="error">{error}</p>
      </>
    );
  }
  if (!detail) return null;

  const kb = detail.knowledge_base;
  const memberCount = detail.members.filter((m) => m.status === "active").length;
  const pendingCount = detail.members.filter((m) => m.status === "pending").length;

  return (
    <>
      <div className="breadcrumb">
        <Link href="/kbs">Knowledge bases</Link>
        <span>/</span>
        <span className="mono">{kb.kb_id}</span>
      </div>

      <div className="page-header">
        <div>
          <h1>{kb.name}</h1>
          <p className="page-sub">
            <code className="mono">{kb.kb_id}</code>
            {" · "}
            <span className="pill">{kb.role}</span>
            {kb.shared && kb.owner_email ? ` · Owner ${kb.owner_email}` : null}
          </p>
        </div>
      </div>

      <div className="counter-row">
        <span>
          <strong>{detail.push_count}</strong> pushes
        </span>
        <span>
          <strong>{memberCount}</strong> members
        </span>
        <span>
          <strong>{pendingCount}</strong> pending invites
        </span>
      </div>

      <div className="tabs" role="tablist">
        {(
          [
            ["recent", "Activity"],
            ["members", "Members"],
            ["connect", "Settings"],
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
          <h2 className="panel-title">Recent activity</h2>
          {detail.recent_additions.length === 0 ? (
            <p className="empty">No pushes yet.</p>
          ) : (
            <div className="list">
              {detail.recent_additions.map((item, index) => (
                <article
                  key={`${item.memory_id || item.accepted_at}-${index}`}
                  className="list-item"
                >
                  <p className="meta">
                    {formatWhen(item.accepted_at)}
                    {item.writer_email ? ` · ${item.writer_email}` : ""}
                    {item.client_id ? ` · ${item.client_id}` : ""}
                    {" · "}
                    <span
                      className={
                        item.status === "completed" ? "pill pill-ok" : "pill"
                      }
                    >
                      {item.status}
                    </span>
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
          <h2 className="panel-title">People with access</h2>
          <div className="table-wrap" style={{ border: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {detail.members.map((member) => (
                  <tr key={`${member.email}-${member.status}`}>
                    <td>{member.email}</td>
                    <td>
                      <span className="pill">{member.role}</span>
                    </td>
                    <td>
                      <span
                        className={
                          member.status === "pending"
                            ? "pill pill-warn"
                            : "pill pill-ok"
                        }
                      >
                        {member.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {detail.me?.role === "owner" ? (
            <form className="row" style={{ marginTop: 16 }} onSubmit={onInvite}>
              <div className="field">
                <label htmlFor="invite_email">Invite by email</label>
                <input
                  id="invite_email"
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="invite_role">Role</label>
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
            <p className="empty" style={{ marginTop: 12 }}>
              Only the owner can invite collaborators.
            </p>
          )}
        </section>
      ) : null}

      {tab === "connect" ? (
        <section className="panel">
          <h2 className="panel-title">MCP connection</h2>
          <p className="meta" style={{ marginBottom: 12 }}>
            Endpoint: <code className="mono">{me?.mcp_url}</code>
          </p>
          <div className="row" style={{ marginBottom: 8 }}>
            <button type="button" className="btn btn-sm" onClick={copySnippet}>
              {copied ? "Copied" : "Copy Cursor config"}
            </button>
          </div>
          <pre className="snippet">{cursorSnippet}</pre>
        </section>
      ) : null}

      {tab === "graph" ? (
        <section className="panel">
          <h2 className="panel-title">Knowledge graph</h2>
          {auth.token ? (
            <GraphExplorer kbId={kbId} token={auth.token} />
          ) : (
            <p className="empty">Sign in required.</p>
          )}
        </section>
      ) : null}
    </>
  );
}
