import type { ReactNode } from "react";

const base =
  "inline-flex items-center justify-center rounded-full px-[22px] py-[11px] text-[17px] font-normal tracking-[-0.374px] transition-transform duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-focus active:scale-95";

const variants = {
  primary: "bg-primary text-on-primary",
  ghost:
    "border border-primary bg-transparent text-primary",
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
    <a href={href} className={`${base} ${variants[variant]} ${className} no-underline hover:no-underline`}>
      {children}
    </a>
  );
}
