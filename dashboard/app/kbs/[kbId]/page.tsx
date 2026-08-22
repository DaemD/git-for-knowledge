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
import { Badge } from "@/components/ui/badge";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

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

  if (!auth.ready) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-6 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!auth.isAuthenticated) {
    return (
      <Card className="mx-auto mt-[12vh] max-w-md py-8">
        <CardHeader>
          <CardTitle>Sign in required</CardTitle>
        </CardHeader>
        <CardContent>
          <Button type="button" onClick={auth.login}>
            Continue with Google
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-6 w-64" />
        <Skeleton className="h-10 w-80" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (error && !detail) {
    return (
      <div className="space-y-4">
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link href="/kbs">Knowledge bases</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>{kbId}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
        <p className="text-sm text-destructive">{error}</p>
      </div>
    );
  }
  if (!detail) return null;

  const kb = detail.knowledge_base;
  const memberCount = detail.members.filter((m) => m.status === "active").length;
  const pendingCount = detail.members.filter((m) => m.status === "pending").length;

  return (
    <div className="space-y-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link href="/kbs">Knowledge bases</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage className="font-mono text-xs">{kb.kb_id}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div>
        <h1 className="font-display text-[26px] font-light tracking-[-0.26px]">
          {kb.name}
        </h1>
        <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <code className="font-mono text-xs">{kb.kb_id}</code>
          <Badge variant="outline">{kb.role}</Badge>
          {kb.shared && kb.owner_email ? (
            <span>Owner {kb.owner_email}</span>
          ) : null}
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Pushes", value: detail.push_count },
          { label: "Members", value: memberCount },
          { label: "Pending invites", value: pendingCount },
          {
            label: "Entities",
            value: overview ? overview.entity_count : "—",
          },
        ].map((kpi) => (
          <Card key={kpi.label} className="gap-2 py-4">
            <CardHeader className="px-4 pb-0">
              <CardDescription>{kpi.label}</CardDescription>
              <CardTitle className="text-2xl tabular-nums">{kpi.value}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      <Tabs
        value={tab}
        onValueChange={(value) => setTab(value as Tab)}
        className="gap-5"
      >
        <TabsList className="flex h-auto w-full flex-wrap justify-start">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="recent">Activity</TabsTrigger>
          <TabsTrigger value="entities">Entities</TabsTrigger>
          <TabsTrigger value="explore">Explore</TabsTrigger>
          <TabsTrigger value="members">Members</TabsTrigger>
          <TabsTrigger value="connect">Settings</TabsTrigger>
        </TabsList>

        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        <TabsContent value="overview">
          <Card>
            <CardHeader className="flex-row items-center justify-between gap-3 space-y-0">
              <CardTitle>Overview</CardTitle>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={overviewLoading}
                onClick={() => void loadOverview(true)}
              >
                {overviewLoading ? "Refreshing…" : "Refresh brief"}
              </Button>
            </CardHeader>
            <CardContent className="space-y-5">
              {overviewLoading && !overview ? (
                <p className="text-sm text-muted-foreground">Generating brief…</p>
              ) : null}

              {overview ? (
                <>
                  <p className="text-xs text-muted-foreground">
                    {overview.entity_count} entities · {overview.edge_count} links
                    {" · "}
                    brief via {overview.brief_source}
                    {overview.brief_cached ? " (cached)" : ""}
                    {overview.updated_at
                      ? ` · ${formatWhen(overview.updated_at)}`
                      : ""}
                  </p>
                  <p className="rounded-lg border border-border bg-muted/40 p-3 font-mono text-[13px] leading-relaxed text-foreground/90">
                    {overview.brief.summary || "No summary yet."}
                  </p>

                  <div className="grid gap-5 md:grid-cols-2">
                    {(
                      [
                        ["Core facts", overview.brief.core_facts],
                        ["People & orgs", overview.brief.key_people_orgs],
                        ["Gaps", overview.brief.gaps],
                        ["Suggested pushes", overview.brief.suggested_pushes],
                      ] as const
                    ).map(([title, items]) => (
                      <div key={title}>
                        <h3 className="mb-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                          {title}
                        </h3>
                        <ul className="list-disc space-y-1 pl-4 text-sm text-foreground/85">
                          {asStringList(items).map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>

                  <div>
                    <h3 className="mb-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                      Top entities
                    </h3>
                    {overview.top_entities.length === 0 ? (
                      <p className="text-sm text-muted-foreground">
                        No entities extracted yet.
                      </p>
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        {overview.top_entities.map((item) => (
                          <button
                            key={item.id}
                            type="button"
                            className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-left text-sm transition-colors hover:border-primary/30 hover:bg-accent/50"
                            onClick={() => {
                              setSelectedEntityId(item.id);
                              setTab("entities");
                            }}
                          >
                            <Badge variant="secondary">{item.kind}</Badge>
                            <strong>{item.label}</strong>
                            <span className="text-xs text-muted-foreground">
                              deg {item.degree}
                            </span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <h3 className="mb-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                      What changed
                    </h3>
                    {overview.recent_changes.length === 0 ? (
                      <p className="text-sm text-muted-foreground">
                        No recent pushes.
                      </p>
                    ) : (
                      <div className="divide-y divide-border">
                        {overview.recent_changes.slice(0, 5).map((item, index) => (
                          <article
                            key={`${item.memory_id || item.accepted_at}-${index}`}
                            className="py-3 first:pt-0 last:pb-0"
                          >
                            <p className="text-xs text-muted-foreground">
                              {formatWhen(item.accepted_at)}
                              {item.writer_email ? ` · ${item.writer_email}` : ""}
                            </p>
                            <p className="mt-1 font-mono text-[13px] leading-relaxed">
                              {item.preview}
                            </p>
                          </article>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              ) : null}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="recent">
          <Card>
            <CardHeader>
              <CardTitle>Recent activity</CardTitle>
            </CardHeader>
            <CardContent>
              {detail.recent_additions.length === 0 ? (
                <p className="text-sm text-muted-foreground">No pushes yet.</p>
              ) : (
                <div className="divide-y divide-border">
                  {detail.recent_additions.map((item, index) => (
                    <article
                      key={`${item.memory_id || item.accepted_at}-${index}`}
                      className="py-3 first:pt-0 last:pb-0"
                    >
                      <p className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <span>
                          {formatWhen(item.accepted_at)}
                          {item.writer_email ? ` · ${item.writer_email}` : ""}
                          {item.client_id ? ` · ${item.client_id}` : ""}
                        </span>
                        <Badge
                          variant={
                            item.status === "completed" ? "default" : "outline"
                          }
                        >
                          {item.status}
                        </Badge>
                      </p>
                      <p className="mt-1 font-mono text-[13px] leading-relaxed">
                        {item.preview}
                      </p>
                    </article>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="entities">
          <Card>
            <CardHeader>
              <CardTitle>Entities</CardTitle>
              <div className="pt-2">
                <Label htmlFor="entity_search" className="sr-only">
                  Search
                </Label>
                <Input
                  id="entity_search"
                  type="search"
                  value={entityQuery}
                  onChange={(e) => setEntityQuery(e.target.value)}
                  placeholder="Name, type, or summary"
                />
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-[minmax(220px,320px)_1fr]">
                <div className="max-h-[70vh] space-y-1 overflow-auto border-r-0 md:border-r md:border-border md:pr-3">
                  {entitiesLoading ? (
                    <p className="text-sm text-muted-foreground">Loading…</p>
                  ) : null}
                  {!entitiesLoading && filteredEntities.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No entities found.
                    </p>
                  ) : null}
                  {filteredEntities.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className={cn(
                        "grid w-full grid-cols-[auto_1fr_auto] items-center gap-2 rounded-lg border border-transparent px-2.5 py-2 text-left text-sm transition-colors",
                        selectedEntityId === item.id
                          ? "border-border bg-accent/60"
                          : "hover:bg-muted/70",
                      )}
                      onClick={() => setSelectedEntityId(item.id)}
                    >
                      <Badge variant="outline">{item.kind}</Badge>
                      <span className="truncate">{item.label}</span>
                      <span className="text-xs text-muted-foreground">
                        deg {item.degree}
                      </span>
                    </button>
                  ))}
                </div>

                <div className="min-h-60">
                  {!selectedEntityId ? (
                    <p className="text-sm text-muted-foreground">
                      Select an entity to inspect.
                    </p>
                  ) : null}
                  {entityDetailLoading ? (
                    <p className="text-sm text-muted-foreground">
                      Loading detail…
                    </p>
                  ) : null}
                  {entityDetail && !entityDetailLoading ? (
                    <div className="space-y-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <h3 className="text-lg font-semibold">
                            {entityDetail.entity.label}
                          </h3>
                          <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                            <Badge variant="secondary">
                              {entityDetail.entity.kind}
                            </Badge>
                            <span>degree {entityDetail.entity.degree}</span>
                            <span>
                              brief via {entityDetail.brief_source}
                              {entityDetail.brief_cached ? " (cached)" : ""}
                            </span>
                          </p>
                        </div>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            void loadEntityDetail(entityDetail.entity.id, true)
                          }
                        >
                          Refresh
                        </Button>
                      </div>
                      <p className="rounded-lg border border-border bg-muted/40 p-3 font-mono text-[13px] leading-relaxed">
                        {entityDetail.brief.headline ||
                          entityDetail.entity.summary ||
                          "No headline."}
                      </p>
                      {entityDetail.brief.why_it_matters ? (
                        <p className="font-mono text-[13px] leading-relaxed text-foreground/85">
                          {entityDetail.brief.why_it_matters}
                        </p>
                      ) : null}

                      <div>
                        <h4 className="mb-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                          Related
                        </h4>
                        <ul className="list-disc space-y-1 pl-4 text-sm">
                          {asStringList(entityDetail.brief.related).map(
                            (item) => (
                              <li key={item}>{item}</li>
                            ),
                          )}
                        </ul>
                        {entityDetail.neighbors.length > 0 ? (
                          <div className="mt-2 flex flex-wrap gap-2">
                            {entityDetail.neighbors.map((n) => (
                              <button
                                key={`${n.id}-${n.predicate}-${n.direction}`}
                                type="button"
                                className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm hover:bg-accent/50"
                                onClick={() => setSelectedEntityId(n.id)}
                              >
                                <Badge variant="outline">{n.predicate}</Badge>
                                <strong>{n.label}</strong>
                              </button>
                            ))}
                          </div>
                        ) : null}
                      </div>

                      <div>
                        <h4 className="mb-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                          Open questions
                        </h4>
                        <ul className="list-disc space-y-1 pl-4 text-sm">
                          {asStringList(entityDetail.brief.open_questions).map(
                            (item) => (
                              <li key={item}>{item}</li>
                            ),
                          )}
                        </ul>
                      </div>

                      <div>
                        <h4 className="mb-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                          Sources
                        </h4>
                        {entityDetail.sources.length === 0 ? (
                          <p className="text-sm text-muted-foreground">
                            No linked source snippets.
                          </p>
                        ) : (
                          <div className="divide-y divide-border">
                            {entityDetail.sources.map((source, index) => (
                              <article
                                key={`${source.memory_id || "src"}-${index}`}
                                className="py-3 first:pt-0"
                              >
                                {source.accepted_at ? (
                                  <p className="text-xs text-muted-foreground">
                                    {formatWhen(source.accepted_at)}
                                  </p>
                                ) : null}
                                <p className="mt-1 font-mono text-[13px] leading-relaxed">
                                  {source.preview}
                                </p>
                              </article>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="explore">
          <Card>
            <CardHeader>
              <CardTitle>Explore</CardTitle>
              <CardDescription>
                Capped neighborhood view for orientation — use Entities for the
                full directory.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {auth.token ? (
                <GraphExplorer kbId={kbId} token={auth.token} limit={40} />
              ) : (
                <p className="text-sm text-muted-foreground">Sign in required.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="members">
          <Card>
            <CardHeader>
              <CardTitle>People with access</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="overflow-hidden rounded-lg border border-border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Email</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {detail.members.map((member) => (
                      <TableRow key={`${member.email}-${member.status}`}>
                        <TableCell>{member.email}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{member.role}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              member.status === "pending"
                                ? "secondary"
                                : "default"
                            }
                          >
                            {member.status}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {detail.me?.role === "owner" ? (
                <form
                  className="flex flex-wrap items-end gap-3"
                  onSubmit={onInvite}
                >
                  <div className="grid min-w-[220px] flex-1 gap-1.5">
                    <Label htmlFor="invite_email">Invite by email</Label>
                    <Input
                      id="invite_email"
                      type="email"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      required
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <Label htmlFor="invite_role">Role</Label>
                    <Select value={inviteRole} onValueChange={setInviteRole}>
                      <SelectTrigger id="invite_role" className="w-28">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="write">write</SelectItem>
                        <SelectItem value="read">read</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button type="submit" disabled={inviting}>
                    {inviting ? "Inviting…" : "Invite"}
                  </Button>
                </form>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Only the owner can invite collaborators.
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="connect">
          <Card>
            <CardHeader>
              <CardTitle>MCP connection</CardTitle>
              <CardDescription>
                Endpoint:{" "}
                <code className="font-mono text-xs">{me?.mcp_url}</code>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button type="button" variant="outline" size="sm" onClick={copySnippet}>
                {copied ? "Copied" : "Copy Cursor config"}
              </Button>
              <pre className="overflow-auto rounded-xl border border-border bg-[#1c1e54] p-4 font-mono text-xs leading-relaxed text-[#c4c8e0]">
                {cursorSnippet}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
