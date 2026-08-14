import { motion } from "framer-motion";
import { AmnesiaDemo } from "./components/AmnesiaDemo";
import { ConnectSection } from "./components/ConnectSection";
import { ExamplesTabs } from "./components/ExamplesTabs";
import { Header } from "./components/Header";
import { HeroMesh } from "./components/HeroMesh";
import { PushFetchDemo } from "./components/PushFetchDemo";
import { ToolsStrip } from "./components/ToolsStrip";
import { ButtonLink } from "./components/ui/Button";
import { FaqAccordion } from "./components/ui/FaqAccordion";

const fade = {
  initial: { opacity: 0, y: 20 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-80px" },
  transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] as const },
};

function SectionHead({
  eyebrow,
  title,
  lede,
}: {
  eyebrow: string;
  title: React.ReactNode;
  lede?: React.ReactNode;
}) {
  return (
    <motion.div {...fade} className="mx-auto max-w-2xl text-center">
      <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-accent">
        {eyebrow}
      </p>
      <h2 className="mt-3 font-display text-4xl font-semibold leading-[1.12] text-ink md:text-5xl">
        {title}
      </h2>
      {lede ? (
        <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed text-muted [&_code]:code-chip">
          {lede}
        </p>
      ) : null}
    </motion.div>
  );
}

export default function App() {
  return (
    <>
      <div className="atmosphere" aria-hidden />
      <div className="relative z-10">
        <Header />
        <main>
          <section className="relative min-h-[min(92vh,920px)] overflow-hidden px-5 pb-16 pt-14 md:pt-20">
            <HeroMesh />
            <motion.div
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
              className="relative mx-auto max-w-3xl text-center"
            >
              <p className="font-display text-5xl font-semibold tracking-tight text-ink md:text-6xl">
                grphly
              </p>
              <h1 className="mt-5 font-display text-3xl font-semibold leading-[1.15] text-ink md:text-[2.75rem]">
                Push in Cursor.
                <br />
                Fetch in Claude or ChatGPT.
              </h1>
              <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed text-muted md:text-lg">
                One knowledge base — not five conflicting mental models. Push
                once from any AI. Your teammates fetch the same truth in
                whatever assistant they use.
              </p>
              <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
                <ButtonLink href="#connect">
                  Connect your AI — free beta
                </ButtonLink>
                <ButtonLink href="#examples" variant="ghost">
                  See real examples
                </ButtonLink>
              </div>
            </motion.div>
            <PushFetchDemo />
          </section>

          <ToolsStrip />

          <section id="why" className="scroll-mt-24 px-5 py-24">
            <SectionHead
              eyebrow="The cost of forgetting"
              title={
                <>
                  You’re paying for AI
                  <br />
                  that has amnesia.
                </>
              }
              lede={
                <>
                  Context windows reset. New chats wipe the slate. Docs rot in
                  Notion. Slack threads die. So you paste the same architecture
                  note — again — and burn tokens explaining what you already
                  decided.
                </>
              }
            />
            <AmnesiaDemo />
            <div className="mx-auto mt-12 grid max-w-3xl gap-4 text-left md:grid-cols-2">
              <div className="rounded-2xl border border-line bg-surface p-6">
                <strong className="text-ink">Without grphly</strong>
                <p className="mt-2 text-sm leading-relaxed text-muted">
                  “We use Postgres, right?” — asked for the 4th time this week.
                  Junior joins, spends half a day reconstructing decisions from
                  old PRs. You switch from Cursor to Claude and start over.
                </p>
              </div>
              <div className="rounded-2xl border border-accent/20 bg-accent-soft/60 p-6">
                <strong className="text-ink">With grphly</strong>
                <p className="mt-2 text-sm leading-relaxed text-muted [&_code]:code-chip">
                  Push the decision once. Any teammate, any assistant, any day —{" "}
                  <code>kb fetch</code> returns the same source of truth. Less
                  re-prompting. Fewer wrong assumptions. Faster shipping.
                </p>
              </div>
            </div>
          </section>

          <section className="px-5 py-24">
            <SectionHead
              eyebrow="Why teams switch"
              title={
                <>
                  Knowledge that survives
                  <br />
                  the chat.
                </>
              }
            />
            <ol className="mx-auto mt-12 max-w-2xl space-y-3 text-left">
              {[
                {
                  t: "Save hours every week",
                  d: "Stop copy-pasting “project context” into every new thread. Your AI already knows the stack, constraints, and “why we did it this way.”",
                },
                {
                  t: "Keep assistants in sync",
                  d: "Push in Cursor. Fetch in Claude Code or ChatGPT. One knowledge base — not five conflicting mental models.",
                },
                {
                  t: "Onboard without a lecture",
                  d: "Invite a teammate. They sign in with Google, connect grphly, and ask the project what matters. No 45-minute voice call.",
                },
                {
                  t: "Feel like git — not another wiki",
                  d: (
                    <>
                      Type <code>kb push</code> / <code>kb fetch</code> in chat.
                      No new app to live in. No ceremony. Just durable memory
                      where you already work.
                    </>
                  ),
                },
              ].map((item, i) => (
                <motion.li
                  key={item.t}
                  {...fade}
                  transition={{ ...fade.transition, delay: i * 0.05 }}
                  whileHover={{ x: 4 }}
                  className="flex gap-4 rounded-xl border border-transparent bg-surface/0 px-4 py-4 transition-colors hover:border-line hover:bg-surface"
                >
                  <span className="font-mono text-sm font-medium text-accent">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <strong className="text-ink">{item.t}</strong>
                    <p className="mt-1 text-sm leading-relaxed text-muted [&_code]:code-chip">
                      {item.d}
                    </p>
                  </div>
                </motion.li>
              ))}
            </ol>
          </section>

          <section id="examples" className="scroll-mt-24 px-5 py-24">
            <SectionHead
              eyebrow="Examples"
              title={
                <>
                  Push whole sessions.
                  <br />
                  Not just one-liners.
                </>
              }
              lede={
                <>
                  <code>kb push</code> takes any durable text — a sentence, a
                  design dump, or a summarized chat from another LLM. Fetch
                  later with a real question.
                </>
              }
            />
            <ExamplesTabs />
          </section>

          <section
            className="relative overflow-hidden px-5 py-24 text-center"
            aria-label="Get started"
          >
            <div className="absolute inset-0 -z-10 bg-ink" />
            <div
              className="absolute inset-0 -z-10 opacity-60"
              style={{
                background:
                  "radial-gradient(ellipse 60% 80% at 20% 50%, rgba(14,124,102,0.4), transparent), radial-gradient(ellipse 50% 70% at 90% 40%, rgba(20,80,70,0.25), transparent)",
              }}
            />
            <h2 className="font-display text-4xl font-semibold leading-tight text-white md:text-5xl">
              Connect your AI.
              <br />
              Stop re-explaining.
            </h2>
            <p className="mx-auto mt-4 max-w-md text-white/65">
              Add grphly as an MCP server. Push once. Fetch in any assistant —
              or invite a teammate to the same knowledge base.
            </p>
            <div className="mt-8">
              <ButtonLink href="#connect">
                Connect your AI — free beta
              </ButtonLink>
            </div>
          </section>

          <section id="pricing" className="scroll-mt-24 px-5 py-24">
            <SectionHead
              eyebrow="Pricing"
              title={
                <>
                  14 days free.
                  <br />
                  Then one simple plan.
                </>
              }
              lede={
                <>
                  Start with a full trial from your first Google sign-in. When it
                  ends, subscribe once — unlock every <code>kb_*</code> tool
                  again.
                </>
              }
            />
            <motion.div
              {...fade}
              whileHover={{ y: -4 }}
              className="mx-auto mt-12 max-w-md rounded-2xl border border-line bg-surface p-8 text-left shadow-[0_30px_70px_-40px_rgba(11,18,32,0.45)]"
            >
              <p className="font-mono text-xs font-medium uppercase tracking-wider text-muted">
                Pro
              </p>
              <p className="mt-2 font-display text-5xl font-semibold text-ink">
                $19
                <span className="ml-2 font-sans text-base font-medium text-muted">
                  / month
                </span>
              </p>
              <ul className="mt-6 space-y-2.5 text-sm text-soft">
                {[
                  "14-day free trial on first login",
                  "Unlimited knowledge bases",
                  "Push & fetch across Cursor, Claude, ChatGPT",
                  "Invite teammates by Google email",
                  "One seat = one Google account",
                ].map((f) => (
                  <li key={f} className="flex gap-2.5">
                    <span className="mt-0.5 text-good">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              <div className="mt-8">
                <ButtonLink href="#connect" className="w-full">
                  Start free in your AI
                </ButtonLink>
              </div>
              <p className="mt-4 text-xs leading-relaxed text-muted [&_code]:code-chip">
                After trial: in chat run <code>kb upgrade</code> — grphly
                returns a Lemon Squeezy checkout link. Payment unlocks your
                account via webhook (no need to reconnect OAuth).
              </p>
            </motion.div>
          </section>

          <section id="commands" className="scroll-mt-24 px-5 py-24">
            <SectionHead
              eyebrow="Commands"
              title={
                <>
                  If you can type git,
                  <br />
                  you can use grphly.
                </>
              }
              lede={
                <>
                  No dashboard homework. In chat, say what you mean — the model
                  calls the MCP tool. Push knowledge like you push code.
                </>
              }
            />
            <div className="mx-auto mt-12 grid max-w-4xl gap-6 md:grid-cols-2">
              <pre className="terminal overflow-x-auto rounded-2xl border border-white/10 p-5 font-mono text-[13px] leading-relaxed text-[#c9d3e4] shadow-[0_24px_60px_-36px_rgba(11,18,32,0.5)]">
                <code>{`kb list
kb create <id> [name]
kb use <id>
kb push <text>
kb fetch <question>
kb invite <email> [read|write]
kb members
kb revoke <email>
kb delete <id>`}</code>
              </pre>
              <div className="space-y-1 rounded-2xl border border-line bg-surface p-2 text-sm">
                {[
                  ["kb push", "store summaries, decisions, research dumps"],
                  ["kb fetch", "ask across what any LLM pushed"],
                  ["kb invite", "give a teammate the same brain"],
                  ["kb list", "see every knowledge base you own"],
                  ["kb create", "one KB per product, client, or idea"],
                  ["kb members", "know who can read or write"],
                ].map(([cmd, desc]) => (
                  <motion.div
                    key={cmd}
                    whileHover={{ backgroundColor: "rgba(221,243,236,0.8)" }}
                    className="flex flex-col gap-0.5 rounded-lg px-3 py-2.5 sm:flex-row sm:items-center sm:justify-between sm:gap-4"
                  >
                    <code className="font-mono text-accent">{cmd}</code>
                    <span className="text-muted sm:text-right">{desc}</span>
                  </motion.div>
                ))}
              </div>
            </div>
          </section>

          <section className="px-5 py-24">
            <SectionHead
              eyebrow="Get value in minutes"
              title={
                <>
                  Connect once.
                  <br />
                  Never start from zero again.
                </>
              }
            />
            <ol className="mx-auto mt-12 grid max-w-3xl gap-3 text-left sm:grid-cols-2">
              {[
                {
                  t: "Connect your AI",
                  d: "Add grphly as an MCP server. Sign in with Google. Under two minutes on Cursor.",
                },
                {
                  t: "Create a knowledge base",
                  d: (
                    <>
                      <code>kb create my-product</code> — one place for that
                      project’s durable truth.
                    </>
                  ),
                },
                {
                  t: "Push what matters",
                  d: "Architecture notes, chat summaries, “never do X.” Anything durable you don’t want trapped in one model’s context window.",
                },
                {
                  t: "Invite the people who ship with you",
                  d: "They connect the same MCP, join the KB, and stop pinging you for context.",
                },
              ].map((item, i) => (
                <motion.li
                  key={item.t}
                  {...fade}
                  whileHover={{ y: -3 }}
                  className="list-none rounded-2xl border border-line bg-surface p-5 shadow-[0_16px_40px_-32px_rgba(11,18,32,0.4)]"
                >
                  <span className="font-mono text-xs font-medium text-accent">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <strong className="mt-2 block text-ink">{item.t}</strong>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted [&_code]:code-chip">
                    {item.d}
                  </p>
                </motion.li>
              ))}
            </ol>
          </section>

          <section id="faq" className="scroll-mt-24 px-5 py-24">
            <SectionHead
              eyebrow="FAQ"
              title={
                <>
                  What you need
                  <br />
                  to know.
                </>
              }
            />
            <FaqAccordion
              items={[
                {
                  q: "What is grphly?",
                  a: "A shared knowledge base for your AI tools and team. Push durable decisions from Cursor, Claude, or ChatGPT; fetch the same truth in any assistant. Feels like git for project memory — not another wiki.",
                },
                {
                  q: "Do I need a new app?",
                  a: (
                    <>
                      No. Connect grphly as an MCP server in the AI you already
                      use. Type <code>kb push</code> / <code>kb fetch</code> in
                      chat. No dashboard homework.
                    </>
                  ),
                },
                {
                  q: "How does the free trial work?",
                  a: (
                    <>
                      14 days from your first Google sign-in. Then run{" "}
                      <code>kb upgrade</code> in chat for Lemon Squeezy
                      checkout — Pro is $19/month per seat.
                    </>
                  ),
                },
                {
                  q: "Can teammates share a knowledge base?",
                  a: (
                    <>
                      Yes. Invite by Google email with <code>kb invite</code>.
                      They connect the same MCP, join the KB, and fetch what you
                      pushed.
                    </>
                  ),
                },
                {
                  q: "Which tools work?",
                  a: "Cursor, Antigravity, Claude Code, Claude, and ChatGPT today — any client that supports remote MCP + OAuth.",
                },
              ]}
            />
          </section>

          <ConnectSection />

          <section className="px-5 py-28 text-center">
            <h2 className="font-display text-4xl font-semibold leading-tight text-ink md:text-5xl">
              Your next chat
              <br />
              doesn’t have to be blank.
            </h2>
            <p className="mx-auto mt-5 max-w-md text-muted">
              Connect grphly once. Push the facts you’re tired of repeating.
              Tomorrow’s AI — and your teammates — already know.
            </p>
            <div className="mt-8">
              <ButtonLink href="#connect">
                Connect your AI — free beta
              </ButtonLink>
            </div>
          </section>
        </main>

        <footer className="border-t border-line bg-surface/60 px-5 py-8">
          <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-2 text-sm text-muted sm:flex-row">
            <span className="font-display text-lg font-semibold text-ink">
              grphly
            </span>
            <span>Early beta · Google sign-in · shared knowledge for MCP</span>
          </div>
        </footer>
      </div>
    </>
  );
}
