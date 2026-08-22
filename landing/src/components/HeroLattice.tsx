import { useId, useMemo } from "react";
import { useReducedMotion } from "framer-motion";

const SIZE = 36;
const CX = 560;
const CY = 318;
const RADIUS = 6;

type Axial = { q: number; r: number };

function hexPixel(q: number, r: number) {
  return {
    x: CX + SIZE * (1.5 * q),
    y: CY + SIZE * ((Math.sqrt(3) / 2) * q + Math.sqrt(3) * r),
  };
}

function cubeDist(q: number, r: number) {
  return (Math.abs(q) + Math.abs(q + r) + Math.abs(r)) / 2;
}

function key(q: number, r: number) {
  return `${q},${r}`;
}

const DIRS: Axial[] = [
  { q: 1, r: 0 },
  { q: 1, r: -1 },
  { q: 0, r: -1 },
  { q: -1, r: 0 },
  { q: -1, r: 1 },
  { q: 0, r: 1 },
];

function ringPolygon(dist: number) {
  const pts: string[] = [];
  for (let i = 0; i < 6; i += 1) {
    const a = (Math.PI / 3) * i - Math.PI / 6;
    const rad = dist * SIZE * Math.sqrt(3);
    pts.push(`${CX + rad * Math.cos(a)},${CY + rad * Math.sin(a)}`);
  }
  return pts.join(" ");
}

function buildCrystal() {
  const nodes: {
    id: string;
    q: number;
    r: number;
    x: number;
    y: number;
    dist: number;
    fill: string;
    radius: number;
  }[] = [];

  for (let q = -RADIUS; q <= RADIUS; q += 1) {
    for (let r = -RADIUS; r <= RADIUS; r += 1) {
      const dist = cubeDist(q, r);
      if (dist > RADIUS) continue;
      const { x, y } = hexPixel(q, r);
      let fill = "rgba(255,255,255,0.22)";
      if (dist === 0) fill = "#533afd";
      else if (dist === 1) fill = "#665efd";
      else if (dist === 2) fill = "#b9b9f9";
      else if (dist === 3) fill = "#c5b4f7";
      else if (dist === 4) fill = "rgba(245,233,212,0.85)";
      nodes.push({
        id: key(q, r),
        q,
        r,
        x,
        y,
        dist,
        fill,
        radius: dist === 0 ? 9.5 : dist === 1 ? 5.6 : dist <= 3 ? 4.2 : 3.1,
      });
    }
  }

  const accents: { q: number; r: number; fill: string; radius: number }[] = [
    { q: 4, r: -2, fill: "#ea2261", radius: 6.2 },
    { q: -3, r: 5, fill: "#f96bee", radius: 6.2 },
    { q: -2, r: -3, fill: "#edc08a", radius: 6.2 },
  ];
  for (const a of accents) {
    const n = nodes.find((node) => node.q === a.q && node.r === a.r);
    if (n) {
      n.fill = a.fill;
      n.radius = a.radius;
    }
  }

  const byId = new Map(nodes.map((n) => [n.id, n]));
  const edges: { id: string; x1: number; y1: number; x2: number; y2: number; core: boolean }[] =
    [];
  const seen = new Set<string>();

  for (const n of nodes) {
    for (const d of DIRS) {
      const id2 = key(n.q + d.q, n.r + d.r);
      const other = byId.get(id2);
      if (!other) continue;
      const edgeId = [n.id, id2].sort().join("|");
      if (seen.has(edgeId)) continue;
      seen.add(edgeId);
      edges.push({
        id: edgeId,
        x1: n.x,
        y1: n.y,
        x2: other.x,
        y2: other.y,
        core: n.dist <= 2 && other.dist <= 2,
      });
    }
  }

  const walk = (steps: Axial[]) =>
    steps
      .map((s, i) => {
        const p = hexPixel(s.q, s.r);
        return `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`;
      })
      .join(" ");

  const pulseA = walk([
    { q: 6, r: -3 },
    { q: 5, r: -2 },
    { q: 4, r: -2 },
    { q: 3, r: -1 },
    { q: 2, r: -1 },
    { q: 1, r: 0 },
    { q: 0, r: 0 },
    { q: -1, r: 1 },
    { q: -2, r: 2 },
    { q: -3, r: 3 },
    { q: -3, r: 4 },
    { q: -3, r: 5 },
  ]);

  const pulseB = walk([
    { q: -4, r: -2 },
    { q: -3, r: -2 },
    { q: -2, r: -3 },
    { q: -1, r: -2 },
    { q: 0, r: -1 },
    { q: 0, r: 0 },
    { q: 1, r: 0 },
    { q: 2, r: 1 },
    { q: 3, r: 1 },
    { q: 4, r: 0 },
    { q: 5, r: 0 },
  ]);

  return { nodes, edges, pulseA, pulseB };
}

export function HeroLattice() {
  const raw = useId().replace(/:/g, "");
  const glow = `hero-glow-${raw}`;
  const reduce = useReducedMotion();
  const crystal = useMemo(buildCrystal, []);

  return (
    <div
      className="mockup-shadow relative mx-auto mt-12 w-full max-w-5xl overflow-hidden rounded-xl bg-brand-dark-900"
      aria-label="Structural knowledge lattice"
    >
      <svg
        viewBox="0 0 1120 636"
        className="block h-auto w-full"
        role="img"
        aria-hidden
      >
        <defs>
          <radialGradient id={`${glow}-bg`} cx="50%" cy="46%" r="58%">
            <stop offset="0%" stopColor="#533afd" stopOpacity="0.28" />
            <stop offset="42%" stopColor="#1c1e54" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#0d253d" stopOpacity="1" />
          </radialGradient>
          <filter id={glow} x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="4.5" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <rect width="1120" height="636" fill={`url(#${glow}-bg)`} />

        {[2, 4, 6].map((d) => (
          <polygon
            key={d}
            points={ringPolygon(d)}
            fill="none"
            stroke="rgba(185,185,249,0.14)"
            strokeWidth="1"
          />
        ))}

        {crystal.edges.map((e) => (
          <line
            key={e.id}
            x1={e.x1}
            y1={e.y1}
            x2={e.x2}
            y2={e.y2}
            stroke={e.core ? "rgba(102,94,253,0.55)" : "rgba(185,185,249,0.16)"}
            strokeWidth={e.core ? 1.35 : 0.9}
          />
        ))}

        {!reduce ? (
          <>
            <path
              d={crystal.pulseA}
              fill="none"
              stroke="#533afd"
              strokeWidth="2.2"
              strokeLinecap="round"
              className="hero-pulse-a"
            />
            <path
              d={crystal.pulseB}
              fill="none"
              stroke="#f96bee"
              strokeWidth="1.8"
              strokeLinecap="round"
              className="hero-pulse-b"
            />
            <circle r="4.2" fill="#ffffff" filter={`url(#${glow})`}>
              <animateMotion dur="5.5s" repeatCount="indefinite" path={crystal.pulseA} />
            </circle>
            <circle r="3.4" fill="#ea2261" filter={`url(#${glow})`}>
              <animateMotion dur="7s" repeatCount="indefinite" path={crystal.pulseB} />
            </circle>
          </>
        ) : (
          <>
            <path d={crystal.pulseA} fill="none" stroke="#533afd" strokeWidth="2" />
            <path d={crystal.pulseB} fill="none" stroke="#f96bee" strokeWidth="1.6" />
          </>
        )}

        {crystal.nodes.map((n) => (
          <circle
            key={n.id}
            cx={n.x}
            cy={n.y}
            r={n.radius}
            fill={n.fill}
            filter={n.dist <= 1 ? `url(#${glow})` : undefined}
          />
        ))}
      </svg>
    </div>
  );
}
