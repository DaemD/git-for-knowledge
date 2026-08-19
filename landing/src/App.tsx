import { ProductVideo } from "./components/ProductVideo";
import { AmnesiaDemo } from "./components/AmnesiaDemo";
import { ConnectSection } from "./components/ConnectSection";
import { ExamplesTabs } from "./components/ExamplesTabs";
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
  title: React.ReactNode;
  lede?: React.ReactNode;
  dark?: boolean;
}) {
  return (
    <div className="mx-auto max-w-[680px] text-center">
      {eyebrow ? (
        <p
          className={`text-[21px] font-semibold tracking-[0.231px] ${
            dark ? "text-body-muted" : "text-ink-muted-80"
          }`}
        >
          {eyebrow}
        </p>
      ) : null}
      <h2
        className={`mt-2 text-[40px] font-semibold leading-[1.1] tracking-tight max-md:text-[34px] ${
          dark ? "text-on-dark" : "text-ink"
        }`}
      >
        {title}
      </h2>
      {lede ? (
        <p
          className={`mx-auto mt-4 max-w-xl text-[21px] font-normal leading-[1.19] tracking-[0.231px] [&_code]:code-chip ${
            dark ? "text-body-muted" : "text-ink-muted-80"
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
        <section className="tile-pad bg-canvas text-center">
          <p className="text-[21px] font-semibold tracking-[0.231px] text-ink">
            grphly
          </p>
          <h1 className="mx-auto mt-3 max-w-[820px] text-[56px] font-semibold leading-[1.07] tracking-[-0.28px] max-md:text-[34px]">
            Push in Cursor.
            <br />
            Fetch in Claude or ChatGPT.
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-[28px] font-normal leading-[1.14] tracking-[0.196px] text-ink-muted-80 max-md:text-[21px]">
            One knowledge base — not five conflicting mental models.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <ButtonLink href="#connect">Connect your AI</ButtonLink>
            <ButtonLink href="#examples" variant="ghost">
              Learn more
            </ButtonLink>
          </div>
          <ProductVideo />
        </section>

        <ToolsStrip />

        <section id="why" className="tile-pad scroll-mt-11 bg-parchment">
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
          <AmnesiaDemo />
          <div className="mx-auto mt-12 grid max-w-[980px] gap-6 text-left md:grid-cols-2">
            <div className="rounded-[18px] border border-hairline bg-canvas p-6">
              <strong className="text-[17px] font-semibold tracking-[-0.374px]">
                Without grphly
              </strong>
              <p className="mt-2 text-[17px] leading-[1.47] text-ink-muted-80">
                “We use Postgres, right?” — asked for the 4th time this week.
                Junior joins, spends half a day reconstructing decisions from
                old PRs. You switch from Cursor to Claude and start over.
              </p>
            </div>
            <div className="rounded-[18px] border border-hairline bg-canvas p-6">
              <strong className="text-[17px] font-semibold tracking-[-0.374px]">
                With grphly
              </strong>
              <p className="mt-2 text-[17px] leading-[1.47] text-ink-muted-80 [&_code]:code-chip">
                Push the decision once. Any teammate, any assistant, any day —{" "}
                <code>kb fetch</code> returns the same source of truth. Less
                re-prompting. Fewer wrong assumptions. Faster shipping.
              </p>
            </div>
          </div>
        </section>

        <section className="tile-pad bg-tile text-center">
          <TileHead
            dark
            eyebrow="Why teams switch"
            title={
              <>
                Knowledge that survives
                <br />
                the chat.
              </>
            }
          />
          <ol className="mx-auto mt-12 max-w-[680px] space-y-8 text-left">
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
                <span className="text-[14px] text-primary-on-dark">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <div>
                  <strong className="text-[17px] font-semibold text-on-dark">
                    {item.t}
                  </strong>
                  <p className="mt-1 text-[17px] leading-[1.47] text-body-muted [&_code]:code-chip">
                    {item.d}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section id="examples" className="tile-pad scroll-mt-11 bg-canvas">
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
          className="relative overflow-hidden bg-void px-5 py-24 text-center"
          aria-label="Get started"
        >
          <video
            className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-35"
            src="/hero-graph.mp4"
            autoPlay
            muted
            loop
            playsInline
            aria-hidden
          />
          <div className="relative">
            <h2 className="text-[40px] font-semibold leading-[1.1] text-on-dark max-md:text-[34px]">
              Connect your AI.
              <br />
              Stop re-explaining.
            </h2>
            <p className="mx-auto mt-4 max-w-md text-[17px] leading-[1.47] text-body-muted">
              Add grphly as an MCP server. Push once. Fetch in any assistant —
              or invite a teammate to the same knowledge base.
            </p>
            <div className="mt-8">
              <ButtonLink href="#connect">Connect your AI</ButtonLink>
            </div>
          </div>
        </section>

        <section id="pricing" className="tile-pad scroll-mt-11 bg-parchment">
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
          <div className="mx-auto mt-12 max-w-md rounded-[18px] border border-hairline bg-canvas p-8 text-left">
            <p className="text-[14px] font-semibold tracking-[-0.224px] text-ink-muted-48">
              Pro
            </p>
            <p className="mt-2 text-[56px] font-semibold leading-[1.07] tracking-[-0.28px] text-ink max-md:text-[40px]">
              $19
              <span className="ml-2 text-[17px] font-normal text-ink-muted-48">
                / month
              </span>
            </p>
            <ul className="mt-6 space-y-2.5 text-[17px] text-ink">
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
            <p className="mt-4 text-[12px] leading-[1.3] tracking-[-0.12px] text-ink-muted-48 [&_code]:code-chip">
              After trial: in chat run <code>kb upgrade</code> — grphly returns
              a Lemon Squeezy checkout link.
            </p>
          </div>
        </section>

        <section id="commands" className="tile-pad scroll-mt-11 bg-canvas">
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
          <div className="mx-auto mt-12 grid max-w-[980px] gap-6 md:grid-cols-2">
            <pre className="product-shadow overflow-x-auto rounded-[18px] bg-tile-3 p-5 font-mono text-[13px] leading-relaxed tracking-normal text-body-muted">
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
            <div className="space-y-1 rounded-[18px] border border-hairline bg-canvas p-2 text-[17px]">
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
                  className="flex flex-col gap-0.5 rounded-[11px] px-3 py-2.5 sm:flex-row sm:items-center sm:justify-between sm:gap-4"
                >
                  <code className="font-mono text-[14px] tracking-normal text-primary">
                    {cmd}
                  </code>
                  <span className="text-[14px] text-ink-muted-48 sm:text-right">
                    {desc}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="tile-pad bg-tile">
          <TileHead
            dark
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
                className="list-none rounded-[18px] bg-tile-2 p-6"
              >
                <span className="text-[14px] text-primary-on-dark">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <strong className="mt-2 block text-[17px] font-semibold text-on-dark">
                  {item.t}
                </strong>
                <p className="mt-1.5 text-[17px] leading-[1.47] text-body-muted [&_code]:code-chip">
                  {item.d}
                </p>
              </li>
            ))}
          </ol>
        </section>

        <section id="faq" className="tile-pad scroll-mt-11 bg-parchment">
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

        <section className="tile-pad bg-canvas text-center">
          <PushFetchDemo />
          <h2 className="mt-14 text-[40px] font-semibold leading-[1.1] text-ink max-md:text-[34px]">
            Your next chat
            <br />
            doesn’t have to be blank.
          </h2>
          <p className="mx-auto mt-5 max-w-md text-[17px] leading-[1.47] text-ink-muted-80">
            Connect grphly once. Push the facts you’re tired of repeating.
            Tomorrow’s AI — and your teammates — already know.
          </p>
          <div className="mt-8">
            <ButtonLink href="#connect">Connect your AI</ButtonLink>
          </div>
        </section>
      </main>

      <footer className="bg-parchment px-5 py-16">
        <div className="mx-auto flex max-w-[980px] flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <span className="text-[17px] font-semibold tracking-[-0.374px] text-ink">
            grphly
          </span>
          <span className="text-[12px] tracking-[-0.12px] text-ink-muted-48">
            Early beta · Google sign-in · shared knowledge for MCP
          </span>
        </div>
      </footer>
    </div>
  );
}
