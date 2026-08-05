"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { GraphExplorer } from "@/components/GraphExplorer";
import {
  apiGet,
  apiPost,
  type EntityDetail,
  type EntityListItem,
  type EntityListResult,
  type KbDetail,
  type KbOverview,
  type Me,
} from "@/lib/api";

type Tab =
  | "overview"
  | "recent"
  | "entities"
  | "explore"
  | "members"
  | "connect";

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

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item)).filter(Boolean);
}

export default function KnowledgeBaseDetailPage() {
  const params = useParams<{ kbId: string }>();
  const kbId = decodeURIComponent(params.kbId);
  const auth = useAuth();
  const [tab, setTab] = useState<Tab>("overview");
  const [detail, setDetail] = useState<KbDetail | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [overview, setOverview] = useState<KbOverview | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [entities, setEntities] = useState<EntityListItem[]>([]);
  const [entitiesLoading, setEntitiesLoading] = useState(false);
  const [entityQuery, setEntityQuery] = useState("");
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [entityDetail, setEntityDetail] = useState<EntityDetail | null>(null);
  const [entityDetailLoading, setEntityDetailLoading] = useState(false);
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

  const loadOverview = useCallback(
    async (refresh = false) => {
      if (!auth.token) return;
      setOverviewLoading(true);
      setError(null);
      try {
        const qs = refresh ? "?refresh=1" : "";
        const payload = await apiGet<KbOverview>(
          `/api/v1/kbs/${encodeURIComponent(kbId)}/overview${qs}`,
          auth.token,
        );
        setOverview(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load overview");
      } finally {
        setOverviewLoading(false);
      }
    },
    [auth.token, kbId],
  );

  const loadEntities = useCallback(
    async (q = "") => {
      if (!auth.token) return;
      setEntitiesLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (q.trim()) params.set("q", q.trim());
        const qs = params.toString() ? `?${params}` : "";
        const payload = await apiGet<EntityListResult>(
          `/api/v1/kbs/${encodeURIComponent(kbId)}/entities${qs}`,
          auth.token,
        );
        setEntities(payload.entities);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load entities");
      } finally {
        setEntitiesLoading(false);
      }
    },
    [auth.token, kbId],
  );

  const loadEntityDetail = useCallback(
    async (entityId: string, refresh = false) => {
      if (!auth.token) return;
      setEntityDetailLoading(true);
      setError(null);
      try {
        const qs = refresh ? "?refresh=1" : "";
        const payload = await apiGet<EntityDetail>(
          `/api/v1/kbs/${encodeURIComponent(kbId)}/entities/${encodeURIComponent(entityId)}${qs}`,
          auth.token,
        );
        setEntityDetail(payload);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load entity detail",
        );
      } finally {
        setEntityDetailLoading(false);
      }
    },
    [auth.token, kbId],
  );

  useEffect(() => {
    if (!auth.ready || !auth.isAuthenticated || !auth.token) return;
    void load();
  }, [auth.isAuthenticated, auth.ready, auth.token, load]);

  useEffect(() => {
    if (!auth.token || tab !== "overview") return;
    if (!overview) void loadOverview();
  }, [auth.token, loadOverview, overview, tab]);

  useEffect(() => {
    if (!auth.token || tab !== "entities") return;
    if (entities.length === 0) void loadEntities();
  }, [auth.token, entities.length, loadEntities, tab]);

  const filteredEntities = useMemo(() => {
    const q = entityQuery.trim().toLowerCase();
    if (!q) return entities;
    return entities.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        item.kind.toLowerCase().includes(q) ||
        (item.summary || "").toLowerCase().includes(q),
    );
  }, [entities, entityQuery]);

  useEffect(() => {
    if (!auth.token || !selectedEntityId) return;
    void loadEntityDetail(selectedEntityId);
  }, [auth.token, loadEntityDetail, selectedEntityId]);

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
        {overview ? (
          <span>
            <strong>{overview.entity_count}</strong> entities
          </span>
        ) : null}
      </div>

      <div className="tabs" role="tablist">
        {(
          [
            ["overview", "Overview"],
            ["recent", "Activity"],
            ["entities", "Entities"],
            ["explore", "Explore"],
            ["members", "Members"],
            ["connect", "Settings"],
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

      {tab === "overview" ? (
        <section className="panel">
          <div className="row" style={{ marginBottom: 12 }}>
            <h2 className="panel-title" style={{ margin: 0, flex: 1 }}>
              Overview
            </h2>
            <button
              type="button"
              className="btn btn-sm"
              disabled={overviewLoading}
              onClick={() => void loadOverview(true)}
            >
              {overviewLoading ? "Refreshing…" : "Refresh brief"}
            </button>
          </div>

          {overviewLoading && !overview ? (
            <p className="empty">Generating brief…</p>
          ) : null}

          {overview ? (
            <>
              <p className="meta" style={{ marginBottom: 12 }}>
                {overview.entity_count} entities · {overview.edge_count} links
                {" · "}
                brief via {overview.brief_source}
                {overview.brief_cached ? " (cached)" : ""}
                {overview.updated_at
                  ? ` · ${formatWhen(overview.updated_at)}`
                  : ""}
              </p>
              <p className="preview" style={{ marginBottom: 16 }}>
                {overview.brief.summary || "No summary yet."}
              </p>

              <div className="overview-grid">
                <div>
                  <h3 className="section-label">Core facts</h3>
                  <ul className="bullet-list">
                    {asStringList(overview.brief.core_facts).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="section-label">People & orgs</h3>
                  <ul className="bullet-list">
                    {asStringList(overview.brief.key_people_orgs).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="section-label">Gaps</h3>
                  <ul className="bullet-list">
                    {asStringList(overview.brief.gaps).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="section-label">Suggested pushes</h3>
                  <ul className="bullet-list">
                    {asStringList(overview.brief.suggested_pushes).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>

              <h3 className="section-label" style={{ marginTop: 20 }}>
                Top entities
              </h3>
              {overview.top_entities.length === 0 ? (
                <p className="empty">No entities extracted yet.</p>
              ) : (
                <div className="entity-chips">
                  {overview.top_entities.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className="entity-chip"
                      onClick={() => {
                        setSelectedEntityId(item.id);
                        setTab("entities");
                      }}
                    >
                      <span className="pill">{item.kind}</span>
                      <strong>{item.label}</strong>
                      <span className="meta">deg {item.degree}</span>
                    </button>
                  ))}
                </div>
              )}

              <h3 className="section-label" style={{ marginTop: 20 }}>
                What changed
              </h3>
              {overview.recent_changes.length === 0 ? (
                <p className="empty">No recent pushes.</p>
              ) : (
                <div className="list">
                  {overview.recent_changes.slice(0, 5).map((item, index) => (
                    <article
                      key={`${item.memory_id || item.accepted_at}-${index}`}
                      className="list-item"
                    >
                      <p className="meta">
                        {formatWhen(item.accepted_at)}
                        {item.writer_email ? ` · ${item.writer_email}` : ""}
                      </p>
                      <p className="preview">{item.preview}</p>
                    </article>
                  ))}
                </div>
              )}
            </>
          ) : null}
        </section>
      ) : null}

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

      {tab === "entities" ? (
        <section className="panel">
          <h2 className="panel-title">Entities</h2>
          <div className="row" style={{ marginBottom: 12 }}>
            <div className="field" style={{ flex: 1 }}>
              <label htmlFor="entity_search">Search</label>
              <input
                id="entity_search"
                type="search"
                value={entityQuery}
                onChange={(e) => setEntityQuery(e.target.value)}
                placeholder="Name, type, or summary"
              />
            </div>
          </div>

          <div className="entities-layout">
            <div className="entity-list">
              {entitiesLoading ? <p className="empty">Loading…</p> : null}
              {!entitiesLoading && filteredEntities.length === 0 ? (
                <p className="empty">No entities found.</p>
              ) : null}
              {filteredEntities.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={
                    selectedEntityId === item.id
                      ? "entity-row selected"
                      : "entity-row"
                  }
                  onClick={() => setSelectedEntityId(item.id)}
                >
                  <span className="pill">{item.kind}</span>
                  <span className="entity-row-label">{item.label}</span>
                  <span className="meta">deg {item.degree}</span>
                </button>
              ))}
            </div>

            <div className="entity-detail">
              {!selectedEntityId ? (
                <p className="empty">Select an entity to inspect.</p>
              ) : null}
              {entityDetailLoading ? <p className="empty">Loading detail…</p> : null}
              {entityDetail && !entityDetailLoading ? (
                <>
                  <div className="row" style={{ marginBottom: 8 }}>
                    <div style={{ flex: 1 }}>
                      <h3 style={{ margin: 0 }}>{entityDetail.entity.label}</h3>
                      <p className="meta">
                        <span className="pill">{entityDetail.entity.kind}</span>
                        {" · "}
                        degree {entityDetail.entity.degree}
                        {" · "}
                        brief via {entityDetail.brief_source}
                        {entityDetail.brief_cached ? " (cached)" : ""}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() =>
                        void loadEntityDetail(entityDetail.entity.id, true)
                      }
                    >
                      Refresh
                    </button>
                  </div>
                  <p className="preview">
                    {entityDetail.brief.headline ||
                      entityDetail.entity.summary ||
                      "No headline."}
                  </p>
                  {entityDetail.brief.why_it_matters ? (
                    <p className="preview" style={{ marginTop: 8 }}>
                      {entityDetail.brief.why_it_matters}
                    </p>
                  ) : null}

                  <h4 className="section-label" style={{ marginTop: 16 }}>
                    Related
                  </h4>
                  <ul className="bullet-list">
                    {asStringList(entityDetail.brief.related).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                  {entityDetail.neighbors.length > 0 ? (
                    <div className="entity-chips" style={{ marginTop: 8 }}>
                      {entityDetail.neighbors.map((n) => (
                        <button
                          key={`${n.id}-${n.predicate}-${n.direction}`}
                          type="button"
                          className="entity-chip"
                          onClick={() => setSelectedEntityId(n.id)}
                        >
                          <span className="pill">{n.predicate}</span>
                          <strong>{n.label}</strong>
                        </button>
                      ))}
                    </div>
                  ) : null}

                  <h4 className="section-label" style={{ marginTop: 16 }}>
                    Open questions
                  </h4>
                  <ul className="bullet-list">
                    {asStringList(entityDetail.brief.open_questions).map(
                      (item) => (
                        <li key={item}>{item}</li>
                      ),
                    )}
                  </ul>

                  <h4 className="section-label" style={{ marginTop: 16 }}>
                    Sources
                  </h4>
                  {entityDetail.sources.length === 0 ? (
                    <p className="empty">No linked source snippets.</p>
                  ) : (
                    <div className="list">
                      {entityDetail.sources.map((source, index) => (
                        <article
                          key={`${source.memory_id || "src"}-${index}`}
                          className="list-item"
                        >
                          {source.accepted_at ? (
                            <p className="meta">
                              {formatWhen(source.accepted_at)}
                            </p>
                          ) : null}
                          <p className="preview">{source.preview}</p>
                        </article>
                      ))}
                    </div>
                  )}
                </>
              ) : null}
            </div>
          </div>
        </section>
      ) : null}

      {tab === "explore" ? (
        <section className="panel">
          <h2 className="panel-title">Explore</h2>
          <p className="meta" style={{ marginBottom: 12 }}>
            Capped neighborhood view for orientation — use Entities for the full
            directory.
          </p>
          {auth.token ? (
            <GraphExplorer kbId={kbId} token={auth.token} limit={40} />
          ) : (
            <p className="empty">Sign in required.</p>
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
    </>
  );
}
