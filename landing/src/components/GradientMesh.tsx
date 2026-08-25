import { useId } from "react";

export function GradientMesh({ className = "" }: { className?: string }) {
  const raw = useId().replace(/:/g, "");
  const blurId = `mesh-blur-${raw}`;

  return (
    <svg
      className={className}
      viewBox="0 0 1440 520"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden
    >
      <defs>
        <filter id={blurId} x="-30%" y="-40%" width="160%" height="180%">
          <feGaussianBlur stdDeviation="80" />
        </filter>
      </defs>
      <g filter={`url(#${blurId})`}>
        <ellipse cx="720" cy="80" rx="280" ry="160" fill="#e6b7fe" opacity="0.55" />
        <ellipse cx="620" cy="200" rx="340" ry="220" fill="#9350ff" />
        <ellipse cx="820" cy="180" rx="300" ry="200" fill="#5049c2" />
        <ellipse cx="900" cy="260" rx="260" ry="180" fill="#7873cb" />
        <ellipse cx="540" cy="280" rx="240" ry="160" fill="#0e0aa2" />
        <ellipse cx="720" cy="360" rx="420" ry="180" fill="#000240" />
      </g>
    </svg>
  );
}
