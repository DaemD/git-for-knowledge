import type { ReactNode } from "react";

const base =
  "inline-flex items-center justify-center rounded-md text-[16px] font-normal leading-[1.5] tracking-normal transition-colors duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-link-accent";

const variants = {
  primary:
    "h-14 border border-ink bg-success-emphasis px-7 py-1.5 text-ink",
  ghost:
    "h-14 border border-ink bg-surface-2 px-7 py-1.5 text-link-blue",
  dark: "h-10 border border-ink bg-success-emphasis px-4 py-2 text-[14px] text-ink",
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
  return (
    <a
      href={href}
      className={`${base} ${variants[variant]} ${className} no-underline hover:no-underline`}
    >
      {children}
    </a>
  );
}
