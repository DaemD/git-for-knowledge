import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

const TOOLS = ["Cursor", "Antigravity", "Claude Code", "Claude", "ChatGPT"];

export function ToolsStrip() {
  const reduce = useReducedMotion();
  const [active, setActive] = useState(0);

  useEffect(() => {
    if (reduce) return;
    const id = window.setInterval(
      () => setActive((i) => (i + 1) % TOOLS.length),
      1600,
    );
    return () => window.clearInterval(id);
  }, [reduce]);

  return (
    <section className="border-y border-line bg-surface/70 py-12 backdrop-blur">
      <p className="mb-7 text-center text-sm font-medium text-muted">
        One memory layer across the tools you already pay for
      </p>
      <ul className="mx-auto flex max-w-3xl flex-wrap items-center justify-center gap-2.5 px-4">
        {TOOLS.map((tool, i) => {
          const on = active === i;
          return (
            <motion.li key={tool} layout>
              <button
                type="button"
                onClick={() => setActive(i)}
                className={`relative overflow-hidden rounded-full border px-4 py-2 font-mono text-xs transition-colors ${
                  on
                    ? "border-accent/30 bg-accent text-white"
                    : "border-line bg-paper text-muted hover:border-line-strong hover:text-ink"
                }`}
              >
                {on && !reduce ? (
                  <motion.span
                    layoutId="tool-pill"
                    className="absolute inset-0 -z-10 rounded-full bg-accent"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                ) : null}
                {tool}
              </button>
            </motion.li>
          );
        })}
      </ul>
    </section>
  );
}
