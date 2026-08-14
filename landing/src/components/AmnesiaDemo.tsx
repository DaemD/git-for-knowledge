import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

const PANES = ["Cursor", "Claude", "ChatGPT"] as const;

export function AmnesiaDemo() {
  const reduce = useReducedMotion();
  const [cleared, setCleared] = useState(false);

  useEffect(() => {
    if (reduce) {
      setCleared(true);
      return;
    }
    let cancelled = false;
    async function loop() {
      while (!cancelled) {
        setCleared(false);
        await new Promise((r) => setTimeout(r, 1900));
        if (cancelled) return;
        setCleared(true);
        await new Promise((r) => setTimeout(r, 1500));
      }
    }
    void loop();
    return () => {
      cancelled = true;
    };
  }, [reduce]);

  return (
    <div
      className="mx-auto mt-12 grid max-w-3xl gap-3 sm:grid-cols-3"
      aria-hidden
    >
      {PANES.map((label, i) => (
        <div
          key={label}
          className="relative overflow-hidden rounded-xl border border-line bg-surface px-4 py-5 shadow-[0_12px_40px_-28px_rgba(11,18,32,0.45)]"
        >
          <div className="mb-3 font-mono text-[11px] uppercase tracking-wider text-muted">
            {label}
          </div>
          <AnimatePresence mode="wait">
            {!cleared ? (
              <motion.p
                key="line"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, filter: "blur(5px)", y: -4 }}
                transition={{ duration: 0.35, delay: i * 0.08 }}
                className="text-sm text-soft"
              >
                We use Postgres for the auth service…
              </motion.p>
            ) : (
              <motion.p
                key="cleared"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="font-mono text-xs font-medium text-accent"
              >
                context cleared
              </motion.p>
            )}
          </AnimatePresence>
          {cleared ? (
            <motion.div
              layoutId={`wipe-${label}`}
              className="pointer-events-none absolute inset-0 bg-gradient-to-r from-transparent via-accent-soft/80 to-transparent"
              initial={{ x: "-100%" }}
              animate={{ x: "100%" }}
              transition={{ duration: 0.7 }}
            />
          ) : null}
        </div>
      ))}
    </div>
  );
}
