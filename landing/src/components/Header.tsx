const links = [
  { href: "#why", label: "Why" },
  { href: "#examples", label: "Examples" },
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
  { href: "#connect", label: "Connect" },
];

export function Header() {
  return (
    <header className="sticky top-0 z-50 h-11 bg-void text-on-dark">
      <div className="mx-auto flex h-full max-w-[980px] items-center justify-between gap-4 px-5">
        <a
          href="#"
          className="text-[12px] font-normal tracking-[-0.12px] text-on-dark no-underline hover:no-underline"
        >
          grphly
        </a>
        <nav className="hidden items-center gap-5 md:flex">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="text-[12px] font-normal tracking-[-0.12px] text-on-dark no-underline hover:text-body-muted hover:no-underline"
            >
              {l.label}
            </a>
          ))}
        </nav>
        <a
          href="#connect"
          className="rounded-[8px] bg-ink px-[15px] py-2 text-[14px] font-normal tracking-[-0.224px] text-on-dark no-underline hover:no-underline active:scale-95"
        >
          Connect
        </a>
      </div>
    </header>
  );
}
