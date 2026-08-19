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
          className="relative overflow-hidden rounded-[18px] border border-hairline bg-canvas px-4 py-5"
        >
          <div className="mb-3 text-[12px] tracking-[-0.12px] text-ink-muted-48">
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
                className="text-[17px] text-ink"
              >
                We use Postgres for the auth service…
              </motion.p>
            ) : (
              <motion.p
                key="cleared"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-[14px] font-semibold text-primary"
              >
                context cleared
              </motion.p>
            )}
          </AnimatePresence>
          {cleared ? (
            <motion.div
              layoutId={`wipe-${label}`}
              className="pointer-events-none absolute inset-y-0 w-1/3 bg-parchment"
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
