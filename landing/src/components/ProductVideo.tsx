export function ProductVideo({ className = "" }: { className?: string }) {
  return (
    <video
      className={`mockup-shadow mx-auto mt-12 block w-full max-w-4xl rounded-[16px] bg-brand-dark-900 ${className}`}
      src="/hero-graph.mp4"
      autoPlay
      muted
      loop
      playsInline
      aria-label="Knowledge graph with a traveling light pulse"
    />
  );
}
