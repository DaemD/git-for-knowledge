import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

export function PushFetchDemo() {
  const reduce = useReducedMotion();
  const [cursor, setCursor] = useState("");
  const [claude, setClaude] = useState("");
  const [phase, setPhase] = useState<"push" | "fetch" | "hold">("push");

  useEffect(() => {
    if (reduce) {
      setCursor(
        "> kb push\nAuth uses Postgres + Auth0. Sessions in Redis. Prefer soft deletes.\nok — stored in acme-core",
      );
      setClaude(
        "> kb fetch architecture postgres\nAuth uses Postgres + Auth0. Sessions in Redis. Prefer soft deletes.",
      );
      return;
    }

    let cancelled = false;
    const pushFull =
      "> kb push\nAuth uses Postgres + Auth0. Sessions in Redis. Prefer soft deletes.\nok — stored in acme-core";
    const fetchFull =
      "> kb fetch architecture postgres\nAuth uses Postgres + Auth0. Sessions in Redis. Prefer soft deletes.";

    async function typeText(
      full: string,
      setter: (v: string) => void,
      delay = 14,
    ) {
      setter("");
      for (let i = 1; i <= full.length; i += 1) {
        if (cancelled) return;
        setter(full.slice(0, i));
        await new Promise((r) => setTimeout(r, delay));
      }
    }

    async function loop() {
      while (!cancelled) {
        setPhase("push");
        setClaude("");
        await typeText(pushFull, setCursor, 12);
        if (cancelled) return;
        await new Promise((r) => setTimeout(r, 500));
        setPhase("fetch");
        await typeText(fetchFull, setClaude, 12);
        if (cancelled) return;
        setPhase("hold");
        await new Promise((r) => setTimeout(r, 2400));
      }
    }

    void loop();
    return () => {
      cancelled = true;
    };
  }, [reduce]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 28 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2, duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
      className="terminal relative mx-auto mt-12 w-full max-w-4xl overflow-hidden rounded-2xl border border-white/10 shadow-[0_40px_80px_-30px_rgba(11,18,32,0.55)]"
      aria-label="Live demo: push in Cursor, fetch in Claude"
    >
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
        <span className="size-2.5 rounded-full bg-[#ff5f57]" />
        <span className="size-2.5 rounded-full bg-[#febc2e]" />
        <span className="size-2.5 rounded-full bg-[#28c840]" />
        <span className="ml-3 font-mono text-xs text-white/45">
          grphly · push → fetch
        </span>
        <AnimatePresence mode="wait">
          <motion.span
            key={phase}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="ml-auto rounded-md bg-white/5 px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider text-[#7dceb8]"
          >
            {phase === "push"
              ? "writing"
              : phase === "fetch"
                ? "reading"
                : "synced"}
          </motion.span>
        </AnimatePresence>
      </div>

      {/* Sync beam */}
      <div className="pointer-events-none absolute left-1/2 top-14 hidden h-[calc(100%-3.5rem)] w-px -translate-x-1/2 md:block">
        <div className="h-full w-full bg-gradient-to-b from-transparent via-white/15 to-transparent" />
        {!reduce && (phase === "push" || phase === "fetch") ? (
          <motion.div
            className="absolute left-1/2 size-2 -translate-x-1/2 rounded-full bg-accent shadow-[0_0_16px_#0e7c66]"
            animate={{
              top: phase === "push" ? ["10%", "70%"] : ["70%", "10%"],
              opacity: [0, 1, 1, 0],
            }}
            transition={{ duration: 1.1, ease: "easeInOut", repeat: Infinity }}
          />
        ) : null}
      </div>

      <div className="grid gap-0 md:grid-cols-2">
        <Pane title="Cursor" body={cursor} active={phase === "push"} />
        <Pane title="Claude" body={claude} active={phase === "fetch" || phase === "hold"} />
      </div>
      <p className="border-t border-white/10 px-4 py-3 text-center font-mono text-xs text-white/40">
        push once · fetch anywhere
      </p>
    </motion.div>
  );
}

function Pane({
  title,
  body,
  active,
}: {
  title: string;
  body: string;
  active: boolean;
}) {
  return (
    <motion.div
      animate={{ backgroundColor: active ? "rgba(14,124,102,0.12)" : "rgba(0,0,0,0)" }}
      className="border-white/10 p-5 md:border-r md:last:border-r-0"
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="font-mono text-[11px] uppercase tracking-wider text-white/40">
          {title}
        </div>
        <motion.span
          animate={{ scale: active ? 1 : 0.85, opacity: active ? 1 : 0.35 }}
          className="size-1.5 rounded-full bg-[#7dceb8]"
        />
      </div>
      <pre className="min-h-[8rem] whitespace-pre-wrap font-mono text-[12.5px] leading-relaxed text-[#c9d3e4]">
        {body}
        <span className="animate-pulse text-accent">▍</span>
      </pre>
    </motion.div>
  );
}
