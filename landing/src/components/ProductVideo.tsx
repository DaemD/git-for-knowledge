export function ProductVideo({
  src,
  label,
  className = "",
}: {
  src: string;
  label: string;
  className?: string;
}) {
  return (
    <video
      className={`mockup-shadow mx-auto mt-12 block w-full max-w-4xl rounded-[16px] bg-brand-dark-900 ${className}`}
      src={src}
      autoPlay
      muted
      loop
      playsInline
      aria-label={label}
    />
  );
}
