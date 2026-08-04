"use client";

import type { Node, Relationship } from "@neo4j-nvl/base";
import { InteractiveNvlWrapper } from "@neo4j-nvl/react";
import { useMemo } from "react";
import type { GraphEdge, GraphNode } from "@/components/GraphExplorer";

export default function NvlCanvas({
  nodes,
  edges,
  colors,
  onSelect,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  colors: Record<string, string>;
  onSelect: (node: GraphNode | null) => void;
}) {
  const byId = useMemo(() => {
    const map = new Map<string, GraphNode>();
    for (const node of nodes) map.set(node.id, node);
    return map;
  }, [nodes]);

  const nvlNodes: Node[] = useMemo(
    () =>
      nodes.map((node) => ({
        id: node.id,
        caption: node.label,
        size: 28,
        color: colors[node.kind] || colors.custom || "#9aa0a6",
      })),
    [colors, nodes],
  );

  const nvlRels: Relationship[] = useMemo(
    () =>
      edges.map((edge) => ({
        id: edge.id,
        from: edge.source,
        to: edge.target,
        caption: edge.predicate,
      })),
    [edges],
  );

  return (
    <InteractiveNvlWrapper
      nodes={nvlNodes}
      rels={nvlRels}
      style={{ width: "100%", height: "100%" }}
      nvlOptions={{
        initialZoom: 1,
        disableTelemetry: true,
      }}
      mouseEventCallbacks={{
        onNodeClick: (node) => {
          onSelect(byId.get(node.id) || null);
        },
        onCanvasClick: () => onSelect(null),
        onZoom: true,
        onPan: true,
        onDrag: true,
      }}
    />
  );
}
