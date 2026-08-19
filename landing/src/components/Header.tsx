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
    <header className="sticky top-0 z-50 border-b border-hairline/80 bg-canvas/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-[1200px] items-center justify-between gap-4 px-6">
        <a
          href="#"
          className="text-[15px] font-normal tracking-normal text-ink no-underline hover:no-underline"
        >
          grphly
        </a>
        <nav className="hidden items-center gap-6 md:flex">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="text-[15px] font-light text-ink-mute-2 no-underline hover:text-ink hover:no-underline"
            >
              {l.label}
            </a>
          ))}
        </nav>
        <ButtonLink href="#connect" className="text-[14px]">
          Connect
        </ButtonLink>
      </div>
    </header>
  );
}
