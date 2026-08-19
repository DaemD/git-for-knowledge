import type { ReactNode } from "react";
import { ProductVideo } from "./components/ProductVideo";
import { ConnectSection } from "./components/ConnectSection";
import { ExamplesTabs } from "./components/ExamplesTabs";
import { GradientMesh } from "./components/GradientMesh";
import { Header } from "./components/Header";
import { PushFetchDemo } from "./components/PushFetchDemo";
import { ToolsStrip } from "./components/ToolsStrip";
import { ButtonLink } from "./components/ui/Button";
import { FaqAccordion } from "./components/ui/FaqAccordion";

function TileHead({
  eyebrow,
  title,
  lede,
  dark = false,
}: {
  eyebrow?: string;
  title: ReactNode;
  lede?: ReactNode;
  dark?: boolean;
}) {
  return (
    <div className="mx-auto max-w-[720px] text-center">
      {eyebrow ? (
        <p
          className={`text-[10px] font-normal uppercase tracking-[0.1px] ${
            dark ? "text-primary-soft" : "text-primary-deep"
          }`}
        >
          {eyebrow}
        </p>
      ) : null}
      <h2
        className={`mt-3 text-[48px] font-light leading-[1.15] tracking-[-0.96px] max-md:text-[32px] ${
          dark ? "text-on-primary" : "text-ink"
        }`}
      >
        {title}
      </h2>
      {lede ? (
        <p
          className={`mx-auto mt-4 max-w-xl text-[16px] font-light leading-[1.4] [&_code]:code-chip ${
            dark ? "text-body-muted" : "text-ink-secondary"
          }`}
        >
          {lede}
        </p>
      ) : null}
    </div>
  );
}

export default function App() {
  return (
    <div className="bg-canvas text-ink">
      <Header />
      <main>
        <section className="relative overflow-hidden text-center">
          <GradientMesh className="pointer-events-none absolute inset-x-0 top-0 h-[68%] w-full" />
          <div className="pointer-events-none absolute inset-x-0 top-[28%] h-[42%] bg-gradient-to-b from-transparent to-canvas" />
          <div className="relative tile-pad">
            <p className="text-[10px] font-normal uppercase tracking-[0.1px] text-primary-deep">
              grphly
            </p>
            <h1 className="mx-auto mt-4 max-w-[860px] text-[56px] font-light leading-[1.03] tracking-[-1.4px] max-md:text-[36px]">
              Push in Cursor.
              <br />
              Fetch in Claude or ChatGPT.
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-[16px] font-light leading-[1.4] text-ink-secondary">
              One knowledge base — not five conflicting mental models.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <ButtonLink href="#connect">Connect your AI</ButtonLink>
              <ButtonLink href="#examples" variant="ghost">
                Learn more
              </ButtonLink>
            </div>
            <ProductVideo
              src="/hero-composite.mp4"
              label="Floating product composite: push in an IDE, graph in the center, fetch in another assistant"
            />
          </div>
        </section>

        <ToolsStrip />

        <section id="why" className="tile-pad scroll-mt-14 bg-canvas-soft">
          <TileHead
            eyebrow="The cost of forgetting"
            title={
              <>
                You’re paying for AI
                <br />
                that has amnesia.
              </>
            }
            lede="Context windows reset. New chats wipe the slate. Docs rot in Notion. Slack threads die."
          />
          <ProductVideo
            src="/amnesia-split.mp4"
            label="Split-screen comparison: assistants with amnesia versus a shared knowledge graph"
          />
          <div className="mx-auto mt-12 grid max-w-[980px] gap-6 text-left md:grid-cols-2">
            <div className="card-shadow rounded-lg border border-hairline bg-canvas p-8">
              <strong className="text-[18px] font-light tracking-normal">
                Without grphly
              </strong>
              <p className="mt-2 text-[15px] font-light leading-[1.4] text-ink-secondary">
                “We use Postgres, right?” — asked for the 4th time this week.
                Junior joins, spends half a day reconstructing decisions from
                old PRs. You switch from Cursor to Claude and start over.
              </p>
            </div>
            <div className="card-shadow rounded-lg border border-hairline bg-canvas p-8">
              <strong className="text-[18px] font-light tracking-normal">
                With grphly
              </strong>
              <p className="mt-2 text-[15px] font-light leading-[1.4] text-ink-secondary [&_code]:code-chip">
                Push the decision once. Any teammate, any assistant, any day —{" "}
                <code>kb fetch</code> returns the same source of truth. Less
                re-prompting. Fewer wrong assumptions. Faster shipping.
              </p>
            </div>
          </div>
        </section>

        <section className="tile-pad bg-canvas-cream text-center">
          <TileHead
            eyebrow="Why teams switch"
            title={
              <>
                Knowledge that survives
                <br />
                the chat.
              </>
            }
          />
          <ol className="mx-auto mt-12 max-w-[720px] space-y-8 text-left">
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
              <li key={item.t} className="flex gap-4">
                <span className="text-[14px] font-light tabular-nums tracking-[-0.42px] text-primary">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <div>
                  <strong className="text-[18px] font-light text-ink">
                    {item.t}
                  </strong>
                  <p className="mt-1 text-[15px] font-light leading-[1.4] text-ink-secondary [&_code]:code-chip">
                    {item.d}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section id="examples" className="tile-pad scroll-mt-14 bg-canvas">
          <TileHead
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
                design dump, or a summarized chat from another LLM.
              </>
            }
          />
          <ExamplesTabs />
        </section>

        <section
          className="relative overflow-hidden bg-brand-dark-900 px-5 py-24 text-center"
          aria-label="Get started"
        >
          <video
            className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-30"
            src="/hero-graph.mp4"
            autoPlay
            muted
            loop
            playsInline
            aria-hidden
          />
          <div className="relative">
            <h2 className="text-[48px] font-light leading-[1.15] tracking-[-0.96px] text-on-primary max-md:text-[32px]">
              Connect your AI.
              <br />
              Stop re-explaining.
            </h2>
            <p className="mx-auto mt-4 max-w-md text-[16px] font-light leading-[1.4] text-body-muted">
              Add grphly as an MCP server. Push once. Fetch in any assistant —
              or invite a teammate to the same knowledge base.
            </p>
            <div className="mt-8">
              <ButtonLink href="#connect">Connect your AI</ButtonLink>
            </div>
          </div>
        </section>

        <section id="pricing" className="tile-pad scroll-mt-14 bg-canvas-soft">
          <TileHead
            eyebrow="Pricing"
            title={
              <>
                14 days free.
                <br />
                Then one simple plan.
              </>
            }
            lede="Start with a full trial from your first Google sign-in."
          />
          <div className="mx-auto mt-12 max-w-md rounded-lg bg-brand-dark-900 p-8 text-left text-on-primary">
            <p className="text-[22px] font-light tracking-[-0.22px]">Pro</p>
            <p className="mt-2 text-[26px] font-light leading-[1.12] tracking-[-0.26px] tabular-nums">
              $19
              <span className="ml-2 text-[15px] font-light text-body-muted">
                / month
              </span>
            </p>
            <ul className="mt-6 space-y-2.5 text-[15px] font-light">
              {[
                "14-day free trial on first login",
                "Unlimited knowledge bases",
                "Push & fetch across Cursor, Claude, ChatGPT",
                "Invite teammates by Google email",
                "One seat = one Google account",
              ].map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
            <div className="mt-8">
              <ButtonLink href="#connect">Start free in your AI</ButtonLink>
            </div>
            <p className="mt-4 text-[11px] font-light leading-[1.4] text-body-muted [&_code]:code-chip">
              After trial: in chat run <code>kb upgrade</code> — grphly returns
              a Lemon Squeezy checkout link.
            </p>
          </div>
        </section>

        <section id="commands" className="tile-pad scroll-mt-14 bg-canvas">
          <TileHead
            eyebrow="Commands"
            title={
              <>
                If you can type git,
                <br />
                you can use grphly.
              </>
            }
            lede="No dashboard homework. Push knowledge like you push code."
          />
          <ProductVideo
            src="/commands-dashboard.mp4"
            label="Dashboard mockup: commands, entity table, and knowledge graph"
          />
          <div className="mx-auto mt-10 max-w-[980px]">
            <div className="card-shadow space-y-1 rounded-lg border border-hairline bg-canvas p-4 text-[15px]">
              {[
                ["kb push", "store summaries, decisions, research dumps"],
                ["kb fetch", "ask across what any LLM pushed"],
                ["kb invite", "give a teammate the same brain"],
                ["kb list", "see every knowledge base you own"],
                ["kb create", "one KB per product, client, or idea"],
                ["kb members", "know who can read or write"],
              ].map(([cmd, desc]) => (
                <div
                  key={cmd}
                  className="flex flex-col gap-0.5 rounded-md px-3 py-2.5 sm:flex-row sm:items-center sm:justify-between sm:gap-4"
                >
                  <code className="font-mono text-[14px] tracking-normal text-primary">
                    {cmd}
                  </code>
                  <span className="text-[13px] text-ink-mute sm:text-right">
                    {desc}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="tile-pad bg-canvas-soft">
          <TileHead
            eyebrow="Get value in minutes"
            title={
              <>
                Connect once.
                <br />
                Never start from zero again.
              </>
            }
          />
          <ol className="mx-auto mt-12 grid max-w-[980px] gap-6 text-left sm:grid-cols-2">
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
              <li
                key={item.t}
                className="card-shadow list-none rounded-lg border border-hairline bg-canvas p-8"
              >
                <span className="text-[14px] font-light tabular-nums tracking-[-0.42px] text-primary">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <strong className="mt-2 block text-[18px] font-light text-ink">
                  {item.t}
                </strong>
                <p className="mt-1.5 text-[15px] font-light leading-[1.4] text-ink-secondary [&_code]:code-chip">
                  {item.d}
                </p>
              </li>
            ))}
          </ol>
        </section>

        <section id="faq" className="tile-pad scroll-mt-14 bg-canvas">
          <TileHead
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
                    <code>kb upgrade</code> in chat for Lemon Squeezy checkout —
                    Pro is $19/month per seat.
                  </>
                ),
              },
              {
                q: "Can teammates share a knowledge base?",
                a: (
                  <>
                    Yes. Invite by Google email with <code>kb invite</code>. They
                    connect the same MCP, join the KB, and fetch what you
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

        <section className="tile-pad bg-canvas-soft text-center">
          <PushFetchDemo />
          <h2 className="mt-14 text-[48px] font-light leading-[1.15] tracking-[-0.96px] text-ink max-md:text-[32px]">
            Your next chat
            <br />
            doesn’t have to be blank.
          </h2>
          <p className="mx-auto mt-5 max-w-md text-[16px] font-light leading-[1.4] text-ink-secondary">
            Connect grphly once. Push the facts you’re tired of repeating.
            Tomorrow’s AI — and your teammates — already know.
          </p>
          <div className="mt-8">
            <ButtonLink href="#connect">Connect your AI</ButtonLink>
          </div>
        </section>
      </main>

      <footer className="bg-canvas px-6 py-16">
        <div className="mx-auto flex max-w-[1200px] flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <span className="text-[15px] font-normal text-ink">grphly</span>
          <span className="text-[13px] tracking-[-0.39px] text-ink-mute">
            Early beta · Google sign-in · shared knowledge for MCP
          </span>
        </div>
      </footer>
    </div>
  );
}
