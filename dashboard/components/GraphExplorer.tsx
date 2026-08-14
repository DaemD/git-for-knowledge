"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { apiGet } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

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
  person: "#0e7c66",
  organization: "#3d8b6e",
  location: "#5c6b64",
  concept: "#2a9d8f",
  tool: "#52796f",
  custom: "#84a98c",
};

const NvlCanvas = dynamic(() => import("@/components/NvlCanvas"), {
  ssr: false,
  loading: () => <Skeleton className="h-[360px] w-full" />,
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

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-9 w-48" />
        <Skeleton className="h-[360px] w-full" />
      </div>
    );
  }
  if (error) return <p className="text-sm text-destructive">{error}</p>;
  if (!data || data.nodes.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No entities extracted for this knowledge base yet. Push more knowledge
        and wait a moment for extraction.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-4">
        <div className="grid gap-1.5">
          <Label htmlFor="kind_filter">Filter by type</Label>
          <Select value={kindFilter} onValueChange={setKindFilter}>
            <SelectTrigger id="kind_filter" className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {kinds.map((kind) => (
                <SelectItem key={kind} value={kind}>
                  {kind === "all" ? "All types" : kind}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <p className="text-sm text-muted-foreground">
          {filtered.nodes.length} nodes · {filtered.edges.length} edges
          {data.node_count > limit ? ` · capped at ${limit}` : ""}
        </p>
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-2">
        {Object.entries(KIND_COLORS).map(([kind, color]) => (
          <span
            key={kind}
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground"
          >
            <i
              className="inline-block size-2 rounded-sm"
              style={{ background: color }}
            />
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
        <Card className="gap-3 py-4">
          <CardHeader className="px-4 pb-0">
            <CardTitle className="text-base">Selected entity</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 px-4">
            <p className="flex flex-wrap items-center gap-2 text-sm">
              <Badge variant="secondary">{selected.kind}</Badge>
              <strong>{selected.label}</strong>
            </p>
            <p className="font-mono text-[13px] leading-relaxed text-muted-foreground">
              {selected.summary || "No summary."}
            </p>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
