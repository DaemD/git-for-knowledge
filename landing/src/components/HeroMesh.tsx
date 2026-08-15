import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";

type Node = { id: string; x: number; y: number };

/** Nodes sit low / at the sides so they don't collide with the brand + headline. */
const NODES: Node[] = [
  { id: "c", x: 12, y: 58 },
  { id: "g", x: 50, y: 72 },
  { id: "l", x: 88, y: 56 },
  { id: "t", x: 72, y: 88 },
  { id: "a", x: 28, y: 90 },
];

const EDGES: [string, string][] = [
  ["c", "g"],
  ["g", "l"],
  ["g", "t"],
  ["g", "a"],
  ["c", "a"],
];

export function HeroMesh() {
  const reduce = useReducedMotion();
  const [pulse, setPulse] = useState(0);
  const [hover, setHover] = useState<string | null>(null);

  useEffect(() => {
    if (reduce) return;
    const id = window.setInterval(
      () => setPulse((p) => (p + 1) % EDGES.length),
      1400,
    );
    return () => window.clearInterval(id);
  }, [reduce]);

  const byId = useMemo(
    () => Object.fromEntries(NODES.map((n) => [n.id, n])) as Record<string, Node>,
    [],
  );

  return (
    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden>
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="xMidYMid slice"
        className="h-full w-full opacity-45"
      >
        <defs>
          <linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#0e7c66" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#145046" stopOpacity="0.4" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="1.2" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {EDGES.map(([a, b], i) => {
          const n1 = byId[a];
          const n2 = byId[b];
          const active = pulse === i || hover === a || hover === b;
          return (
            <g key={`${a}-${b}`}>
              <line
                x1={n1.x}
                y1={n1.y}
                x2={n2.x}
                y2={n2.y}
                stroke="url(#edge)"
                strokeWidth={active ? 0.55 : 0.28}
                opacity={active ? 1 : 0.55}
              />
              {!reduce ? (
                <motion.circle
                  r={0.55}
                  fill="#0e7c66"
                  filter="url(#glow)"
                  initial={false}
                  animate={{
                    cx: [n1.x, n2.x],
                    cy: [n1.y, n2.y],
                    opacity: active ? [0, 1, 0] : 0,
                  }}
                  transition={{
                    duration: 1.35,
                    ease: "easeInOut",
                    repeat: Infinity,
                    delay: i * 0.2,
                  }}
                />
              ) : null}
            </g>
          );
        })}

        {NODES.map((n) => {
          const isHub = n.id === "g";
          const on = hover === n.id || isHub;
          return (
            <g key={n.id}>
              <motion.circle
                cx={n.x}
                cy={n.y}
                r={isHub ? 2.8 : 1.8}
                fill={isHub ? "#0e7c66" : "#ffffff"}
                stroke={isHub ? "#0a6352" : "#b5c0ba"}
                strokeWidth={0.3}
                animate={{
                  r: on ? (isHub ? 3.1 : 2.1) : isHub ? 2.8 : 1.8,
                }}
                transition={{ type: "spring", stiffness: 260, damping: 18 }}
                onMouseEnter={() => setHover(n.id)}
                onMouseLeave={() => setHover(null)}
                style={{ pointerEvents: "all" }}
              />
            </g>
          );
        })}
      </svg>
    </div>
  );
}
