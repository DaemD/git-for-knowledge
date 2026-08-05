export type KnowledgeBase = {
  kb_id: string;
  name: string;
  nams_conversation_id: string;
  created_at: string;
  role: string;
  shared: boolean;
  owner_email: string | null;
};

export type Member = {
  email: string;
  role: string;
  status: string;
  user_id: string | null;
};

export type RecentAddition = {
  memory_id: string | null;
  preview: string;
  client_id: string | null;
  status: string;
  accepted_at: string;
  writer_email: string | null;
};

export type Me = {
  user_id: string;
  username: string;
  email: string | null;
  display_name: string | null;
  plan_status: string;
  mcp_url: string;
  oauth_client_id: string | null;
};

export type KbDetail = {
  username: string;
  knowledge_base: KnowledgeBase;
  push_count: number;
  recent_additions: RecentAddition[];
  members: Member[];
  me: Member | null;
};

export type EntityListItem = {
  id: string;
  label: string;
  kind: string;
  summary: string;
  degree: number;
};

export type KbOverview = {
  kb_id: string;
  kb_name: string;
  push_count: number;
  entity_count: number;
  edge_count: number;
  top_entities: EntityListItem[];
  recent_changes: RecentAddition[];
  brief: {
    summary?: string;
    core_facts?: string[];
    key_people_orgs?: string[];
    gaps?: string[];
    suggested_pushes?: string[];
  };
  brief_cached: boolean;
  brief_source: string;
  updated_at: string | null;
};

export type EntityNeighbor = {
  id: string;
  label: string;
  kind: string;
  predicate: string;
  direction: string;
};

export type EntitySource = {
  memory_id: string | null;
  preview: string;
  accepted_at: string | null;
};

export type EntityDetail = {
  kb_id: string;
  entity: EntityListItem;
  neighbors: EntityNeighbor[];
  sources: EntitySource[];
  brief: {
    headline?: string;
    why_it_matters?: string;
    related?: string[];
    open_questions?: string[];
  };
  brief_cached: boolean;
  brief_source: string;
  updated_at: string | null;
};

export type EntityListResult = {
  kb_id: string;
  entities: EntityListItem[];
  total: number;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

export function authDisabled(): boolean {
  return (process.env.NEXT_PUBLIC_AUTH_DISABLED || "").toLowerCase() === "true";
}

export function devSubject(): string {
  return process.env.NEXT_PUBLIC_DEV_SUBJECT || "dashboard-dev";
}

export function devToken(): string {
  return `sub:${devSubject()}`;
}

export async function apiGet<T>(path: string, token: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export async function apiPost<T>(
  path: string,
  token: string,
  body: unknown,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new Error(payload.error || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}
