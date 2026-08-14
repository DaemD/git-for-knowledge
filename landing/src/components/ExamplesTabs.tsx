import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

const EXAMPLES = [
  {
    h: "Cursor session → Claude Code",
    p: "After a long Cursor thread, push the summary into grphly. Next day in Claude Code, fetch it — same stack decisions, no re-brief.",
    code: `kb push """
Session summary (Cursor, auth refactor):
- Auth0 + Google social only; no local passwords
- Access tokens audience = https://grphly-dev.miless.app/mcp
- Callbacks: localhost:8787 + Claude auth_callback
- Rejected: rolling our own JWT store
Open: invite email copy still draft
"""

kb fetch What did we decide about auth and callbacks?`,
  },
  {
    h: "ChatGPT research → team Cursor",
    p: "Cofounder researches pricing and competitors in ChatGPT, pushes the condensed notes. You open Cursor and fetch the market context without reading their chat log.",
    code: `kb push """
ChatGPT research dump — competitor memory tools:
- Mem0: strong SDK, weaker shared-team KB story
- Our wedge: shared kb_id + invite by Google email
- Pricing hypothesis: free solo, paid seats for orgs
Sources discussed: mem0.ai, Reddit MCP threads
"""

kb fetch What's our wedge vs Mem0 and pricing hypothesis?`,
  },
  {
    h: "Claude design review → agency handoff",
    p: "Client constraints come out of a Claude review. Push the full brief into a client KB. Anyone on the account fetches rules instead of reinventing the stack.",
    code: `kb create acme-rebrand "Acme Q2 site"

kb push """
Claude design review — Acme Q2:
Must: custom CSS only, no Tailwind, WCAG AA
Deploy: Vercel, preview URLs for stakeholders
Tone: quiet, technical, no emoji in UI copy
Out of scope: mobile app, CMS migration
"""

kb fetch What CSS and deploy constraints does Acme have?`,
  },
];

export function ExamplesTabs() {
  const [active, setActive] = useState(0);
  const ex = EXAMPLES[active];

  return (
    <div className="mx-auto mt-12 max-w-3xl">
      <div
        className="flex flex-wrap gap-2"
        role="tablist"
        aria-label="Examples"
      >
        {EXAMPLES.map((item, i) => (
          <button
            key={item.h}
            type="button"
            role="tab"
            aria-selected={active === i}
            onClick={() => setActive(i)}
            className={`rounded-full border px-3.5 py-2 text-left text-xs font-medium transition-colors sm:text-sm ${
              active === i
                ? "border-accent bg-accent text-white"
                : "border-line bg-surface text-muted hover:border-line-strong hover:text-ink"
            }`}
          >
            {item.h.split("→")[0].trim()}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.article
          key={ex.h}
          role="tabpanel"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.25 }}
          className="mt-5 overflow-hidden rounded-2xl border border-line bg-surface shadow-[0_24px_60px_-36px_rgba(11,18,32,0.45)]"
        >
          <div className="border-b border-line px-5 py-4">
            <h3 className="text-lg font-semibold text-ink">{ex.h}</h3>
            <p className="mt-1.5 text-sm leading-relaxed text-muted">{ex.p}</p>
          </div>
          <pre className="terminal overflow-x-auto p-5 font-mono text-[12.5px] leading-relaxed text-[#c9d3e4]">
            <code>{ex.code}</code>
          </pre>
        </motion.article>
      </AnimatePresence>
    </div>
  );
}
