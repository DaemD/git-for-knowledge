import { ButtonLink } from "./ui/Button";

const links = [
  { href: "#why", label: "Why" },
  { href: "#examples", label: "Examples" },
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
  { href: "#connect", label: "Connect" },
];

export function Header() {
  return (
    <header className="sticky top-0 z-50 h-16 bg-void text-ink">
      <div className="mx-auto flex h-full max-w-[1200px] items-center justify-between gap-4 px-4">
        <a
          href="#"
          className="text-[16px] font-normal tracking-[0.24px] text-ink no-underline hover:no-underline"
        >
          grphly
        </a>
        <nav className="hidden items-center gap-2 md:flex">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="h-10 px-2 text-[16px] font-normal tracking-[0.24px] text-ink no-underline hover:text-ink-muted hover:no-underline"
            >
              {l.label}
            </a>
          ))}
        </nav>
        <ButtonLink href="#connect" variant="dark" className="h-10 text-[14px]">
          Connect
        </ButtonLink>
      </div>
    </header>
  );
}
