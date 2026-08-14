import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { ButtonLink } from "./ui/Button";

const links = [
  { href: "#why", label: "Why" },
  { href: "#examples", label: "Examples" },
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
  { href: "#connect", label: "Connect" },
];

export function Header() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <motion.header
      initial={{ y: -12, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.45 }}
      className={`sticky top-0 z-50 border-b transition-[background,border-color,box-shadow] duration-300 ${
        scrolled
          ? "border-line bg-paper/80 shadow-[0_8px_30px_-20px_rgba(11,18,32,0.35)] backdrop-blur-xl"
          : "border-transparent bg-transparent"
      }`}
    >
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-5 py-3.5">
        <a
          href="#"
          className="font-display text-[1.65rem] font-semibold tracking-tight text-ink"
        >
          grphly
        </a>
        <nav className="hidden items-center gap-7 text-sm font-medium text-muted md:flex">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="relative transition-colors hover:text-ink after:absolute after:-bottom-1 after:left-0 after:h-px after:w-0 after:bg-accent after:transition-[width] hover:after:w-full"
            >
              {l.label}
            </a>
          ))}
        </nav>
        <ButtonLink href="#connect" className="!px-3.5 !py-2 text-xs">
          Connect free
        </ButtonLink>
      </div>
    </motion.header>
  );
}
