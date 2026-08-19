import { AnimatePresence, motion } from "framer-motion";
import { Check, Copy } from "lucide-react";
import { useState } from "react";
import {
  OAUTH_CLIENT_ID,
  SNIPPETS,
  type ClientId,
} from "@/lib/content";

const CLIENTS: { id: ClientId; label: string }[] = [
  { id: "cursor", label: "Cursor" },
  { id: "antigravity", label: "Antigravity" },
  { id: "claude-code", label: "Claude Code" },
  { id: "claude", label: "Claude" },
  { id: "chatgpt", label: "ChatGPT" },
];

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-2.5 py-1 font-mono text-[11px] tracking-normal text-body-muted"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1600);
      }}
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function Snippet({ label, text }: { label: string; text: string }) {
  return (
    <div className="terminal mt-4 overflow-hidden rounded-[18px]">
      <div className="flex items-center justify-between border-b border-white/10 px-3 py-2">
        <span className="font-mono text-[11px] text-white/45">{label}</span>
        <CopyButton text={text} />
      </div>
      <pre className="overflow-x-auto p-4 font-mono text-[12.5px] leading-relaxed text-[#c9d3e4]">
        <code>{text}</code>
      </pre>
    </div>
  );
}

const STEPS: Record<
  ClientId,
  {
    steps: React.ReactNode[];
    snippets: { label: string; key: keyof typeof SNIPPETS }[];
    note?: React.ReactNode;
  }
> = {
  cursor: {
    steps: [
      <>Open Cursor Settings → MCP, or edit <code>.cursor/mcp.json</code>.</>,
      <>Paste the snippet below (URL + <code>CLIENT_ID</code>) and save.</>,
      <>Refresh the server, then sign in with Google when prompted.</>,
      <>In chat: <code>kb create my-project</code> then <code>kb push …</code></>,
    ],
    snippets: [{ label: ".cursor/mcp.json", key: "cursor" }],
  },
  antigravity: {
    steps: [
      <>In the Agent panel, open <strong>…</strong> → MCP Servers → Manage MCP Servers → View raw config.</>,
      <>Paste the <code>mcp-remote</code> snippet below (native <code>serverUrl</code> often fails Auth0 OAuth on Antigravity).</>,
      <>Ensure Node 18+ is installed, then Refresh. A browser window should open for Google sign-in.</>,
      <>If sign-in fails with a callback error, add <code>http://127.0.0.1:3334/oauth/callback</code> and <code>http://localhost:3334/oauth/callback</code> to the Auth0 app Allowed Callback URLs.</>,
      <>After connect: <code>kb list</code>.</>,
    ],
    snippets: [{ label: "~/.gemini/antigravity/mcp_config.json", key: "antigravity" }],
  },
  "claude-code": {
    steps: [
      <>Run the command below (includes <code>--client-id</code> for Auth0).</>,
      <>Inside Claude Code, run <code>/mcp</code> and complete Google sign-in.</>,
      <>Confirm grphly tools appear, then try <code>kb list</code>.</>,
    ],
    snippets: [{ label: "terminal", key: "claude-code" }],
  },
  claude: {
    steps: [
      <>Open Claude → Settings → Connectors (or MCP servers).</>,
      <>Add a custom connector with the MCP URL below.</>,
      <>If Claude asks for an OAuth client id, paste the client id from above.</>,
      <>Authorize with Google, then type <code>kb list</code>.</>,
    ],
    snippets: [
      { label: "MCP server URL", key: "claude" },
      { label: "OAuth client id", key: "claude-client" },
    ],
  },
  chatgpt: {
    steps: [
      <>ChatGPT Settings → Connectors → enable Developer Mode (where available).</>,
      <>Add a custom connector named grphly. Paste the MCP URL.</>,
      <>Choose OAuth. If asked for a client id, use the one above.</>,
      <>Sign in with Google, enable the connector, try <code>kb list</code>.</>,
    ],
    snippets: [
      { label: "MCP server URL", key: "chatgpt" },
      { label: "OAuth client id", key: "chatgpt-client" },
    ],
    note: (
      <>
        Custom connectors may require a paid ChatGPT plan with Developer Mode.
        Auth0 must allow ChatGPT’s OAuth callback URL for that client.
      </>
    ),
  },
};

export function ConnectSection() {
  const [client, setClient] = useState<ClientId>("cursor");
  const panel = STEPS[client];

  return (
    <section id="connect" className="tile-pad scroll-mt-11 bg-canvas">
      <div className="mx-auto max-w-[680px] text-center">
        <p className="text-[21px] font-semibold tracking-[0.231px] text-ink-muted-80">
          Setup
        </p>
        <h2 className="mt-2 text-[40px] font-semibold leading-[1.1] tracking-tight text-ink max-md:text-[34px]">
          Connect your AI.
          <br />
          Start pushing today.
        </h2>
        <p className="mx-auto mt-5 max-w-xl text-[17px] leading-[1.47] text-ink-muted-80">
          Same endpoint everywhere. Pick your client, paste the snippet
          (includes the OAuth client id), sign in with Google — then run{" "}
          <code className="code-chip">kb push</code> on the first fact you’re
          tired of repeating.
        </p>
        <p className="mx-auto mt-6 max-w-xl rounded-[18px] border border-hairline bg-parchment px-4 py-3 text-[14px] text-ink">
          OAuth client id (Auth0 native / MCP clients):{" "}
          <code className="font-mono tracking-normal text-primary">{OAUTH_CLIENT_ID}</code>
        </p>
      </div>

      <div
        className="mx-auto mt-10 flex max-w-3xl flex-wrap justify-center gap-2"
        role="tablist"
        aria-label="AI clients"
      >
        {CLIENTS.map((c) => (
          <button
            key={c.id}
            type="button"
            role="tab"
            aria-selected={client === c.id}
            onClick={() => setClient(c.id)}
            className={`rounded-full border-2 px-4 py-2 text-[14px] tracking-[-0.224px] ${
              client === c.id
                ? "border-primary-focus bg-canvas text-ink"
                : "border-hairline bg-canvas text-ink"
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={client}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.2 }}
          className="mx-auto mt-8 max-w-3xl rounded-[18px] border border-hairline bg-canvas p-6 text-left"
          role="tabpanel"
        >
          <ol className="list-decimal space-y-2.5 pl-5 text-[17px] leading-[1.47] text-ink [&_code]:code-chip">
            {panel.steps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
          {panel.note ? (
            <p className="mt-4 text-sm text-muted">{panel.note}</p>
          ) : null}
          {panel.snippets.map((s) => (
            <Snippet key={s.key} label={s.label} text={SNIPPETS[s.key]} />
          ))}
        </motion.div>
      </AnimatePresence>
    </section>
  );
}
