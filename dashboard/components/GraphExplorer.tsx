"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { apiGet } from "@/lib/api";

export type GraphNode = {
  id: string;
  label: string;
  kind: string;
  summary: string;
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  predicate: string;
};

type GraphPayload = {
  kb_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
};

const KIND_COLORS: Record<string, string> = {
  person: "#7eb8ff",
  organization: "#9adf9a",
  location: "#e6c07b",
  concept: "#c3a6ff",
  tool: "#f0a0a0",
  custom: "#9aa0a6",
};

const NvlCanvas = dynamic(() => import("@/components/NvlCanvas"), {
  ssr: false,
  loading: () => <p className="empty">Loading graph…</p>,
});

export function GraphExplorer({
  kbId,
  token,
  limit = 40,
}: {
  kbId: string;
  token: string;
  limit?: number;
}) {
  const [data, setData] = useState<GraphPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [kindFilter, setKindFilter] = useState<string>("all");
  const [selected, setSelected] = useState<GraphNode | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void apiGet<GraphPayload>(
      `/api/v1/kbs/${encodeURIComponent(kbId)}/graph?limit=${limit}`,
      token,
    )
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load graph");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [kbId, token, limit]);

  const kinds = useMemo(() => {
    const set = new Set((data?.nodes || []).map((n) => n.kind || "concept"));
    return ["all", ...Array.from(set).sort()];
  }, [data]);

  const filtered = useMemo(() => {
    if (!data) return { nodes: [] as GraphNode[], edges: [] as GraphEdge[] };
    const nodes =
      kindFilter === "all"
        ? data.nodes
        : data.nodes.filter((n) => n.kind === kindFilter);
    const ids = new Set(nodes.map((n) => n.id));
    const edges = data.edges.filter(
      (e) => ids.has(e.source) && ids.has(e.target),
    );
    return { nodes, edges };
  }, [data, kindFilter]);

  if (loading) return <p className="empty">Loading knowledge graph…</p>;
  if (error) return <p className="error">{error}</p>;
  if (!data || data.nodes.length === 0) {
    return (
      <p className="empty">
        No entities extracted for this knowledge base yet. Push more knowledge
        and wait a moment for extraction.
      </p>
    );
  }

  return (
    <div>
      <div className="row" style={{ marginBottom: "0.85rem" }}>
        <div className="field">
          <label htmlFor="kind_filter">Filter by type</label>
          <select
            id="kind_filter"
            value={kindFilter}
            onChange={(e) => setKindFilter(e.target.value)}
          >
            {kinds.map((kind) => (
              <option key={kind} value={kind}>
                {kind === "all" ? "All types" : kind}
              </option>
            ))}
          </select>
        </div>
        <p className="meta" style={{ alignSelf: "end" }}>
          {filtered.nodes.length} nodes · {filtered.edges.length} edges
          {data.node_count > limit ? ` · capped at ${limit}` : ""}
        </p>
      </div>

      <div className="graph-legend">
        {Object.entries(KIND_COLORS).map(([kind, color]) => (
          <span key={kind} className="legend-item">
            <i style={{ background: color }} />
            {kind}
          </span>
        ))}
      </div>

      <div className="graph-stage">
        <NvlCanvas
          nodes={filtered.nodes}
          edges={filtered.edges}
          colors={KIND_COLORS}
          onSelect={setSelected}
        />
      </div>

      {selected ? (
        <div className="panel" style={{ marginTop: 12 }}>
          <h2 className="panel-title">Selected entity</h2>
          <p className="meta">
            <span className="pill">{selected.kind}</span>{" "}
            <strong style={{ color: "var(--text)" }}>{selected.label}</strong>
          </p>
          <p className="preview" style={{ marginTop: 8 }}>
            {selected.summary || "No summary."}
          </p>
        </div>
      ) : null}
    </div>
  );
}
