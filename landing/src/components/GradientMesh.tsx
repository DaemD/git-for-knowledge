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
          <feGaussianBlur stdDeviation="72" />
        </filter>
      </defs>
      <g filter={`url(#${blurId})`}>
        <ellipse cx="160" cy="220" rx="460" ry="280" fill="#f5e9d4" />
        <ellipse cx="480" cy="90" rx="340" ry="230" fill="#edc08a" />
        <ellipse cx="620" cy="280" rx="280" ry="180" fill="#9b6829" opacity="0.45" />
        <ellipse cx="820" cy="170" rx="400" ry="260" fill="#c5b4f7" />
        <ellipse cx="1080" cy="120" rx="380" ry="250" fill="#533afd" />
        <ellipse cx="1240" cy="70" rx="220" ry="160" fill="#f96bee" />
        <ellipse cx="1340" cy="260" rx="320" ry="210" fill="#ea2261" />
      </g>
    </svg>
  );
}
