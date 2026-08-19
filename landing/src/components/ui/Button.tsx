import type { ReactNode } from "react";

const base =
  "inline-flex items-center justify-center rounded-full px-4 py-2 text-[16px] font-normal leading-none tracking-normal transition-colors duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-soft";

const variants = {
  primary: "bg-primary text-on-primary active:bg-primary-press",
  ghost: "border border-primary bg-canvas text-primary active:bg-canvas-soft",
  dark: "bg-brand-dark-900 text-on-primary",
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
