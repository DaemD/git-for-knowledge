export function ProductVideo({ className = "" }: { className?: string }) {
  return (
    <video
      className={`product-shadow mx-auto mt-12 block w-full max-w-4xl rounded-[18px] bg-tile-3 ${className}`}
      src="/hero-graph.mp4"
      autoPlay
      muted
      loop
      playsInline
      aria-label="Knowledge graph with a traveling light pulse"
    />
  );
}
