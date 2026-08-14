import {
  motion,
  useMotionTemplate,
  useMotionValue,
  useSpring,
} from "framer-motion";
import type { ReactNode } from "react";
import { useRef } from "react";

const base =
  "relative inline-flex items-center justify-center overflow-hidden rounded-lg px-5 py-2.5 text-sm font-semibold tracking-tight transition-[box-shadow,background-color] duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent active:scale-[0.98]";

const variants = {
  primary:
    "bg-accent text-white shadow-[0_10px_30px_-12px_rgba(14,124,102,0.55)] hover:bg-accent-hover hover:shadow-[0_14px_34px_-12px_rgba(14,124,102,0.65)]",
  ghost:
    "border border-line-strong bg-surface/80 text-soft backdrop-blur hover:border-accent/40 hover:text-ink",
} as const;

type Variant = keyof typeof variants;

export function Button({
  variant = "primary",
  className = "",
  type = "button",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type={type}
      className={`${base} ${variants[variant]} ${className}`}
      {...props}
    />
  );
}

export function ButtonLink({
  variant = "primary",
  className = "",
  children,
  href,
}: {
  variant?: Variant;
  className?: string;
  children?: ReactNode;
  href: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 280, damping: 20 });
  const sy = useSpring(y, { stiffness: 280, damping: 20 });
  const shineX = useMotionValue(50);
  const shineY = useMotionValue(50);
  const shine = useMotionTemplate`radial-gradient(120px circle at ${shineX}% ${shineY}%, rgba(255,255,255,0.28), transparent 55%)`;

  return (
    <motion.div
      ref={ref}
      style={{ x: sx, y: sy }}
      className="inline-flex"
      onMouseMove={(e) => {
        const el = ref.current;
        if (!el) return;
        const r = el.getBoundingClientRect();
        x.set((e.clientX - r.left - r.width / 2) * 0.18);
        y.set((e.clientY - r.top - r.height / 2) * 0.18);
        shineX.set(((e.clientX - r.left) / r.width) * 100);
        shineY.set(((e.clientY - r.top) / r.height) * 100);
      }}
      onMouseLeave={() => {
        x.set(0);
        y.set(0);
      }}
    >
      <a href={href} className={`${base} ${variants[variant]} ${className}`}>
        {variant === "primary" ? (
          <motion.span
            aria-hidden
            className="pointer-events-none absolute inset-0"
            style={{ background: shine }}
          />
        ) : null}
        <span className="relative z-10">{children}</span>
      </a>
    </motion.div>
  );
}
