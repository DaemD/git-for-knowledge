const TOOLS = ["Cursor", "Antigravity", "Claude Code", "Claude", "ChatGPT"];

export function ToolsStrip() {
  return (
    <section className="bg-parchment py-16">
      <p className="mb-7 text-center text-[14px] tracking-[-0.224px] text-ink-muted-48">
        One memory layer across the tools you already pay for
      </p>
      <ul className="mx-auto flex max-w-3xl flex-wrap items-center justify-center gap-2 px-4">
        {TOOLS.map((tool) => (
          <li
            key={tool}
            className="rounded-full border border-hairline bg-canvas px-4 py-2 text-[14px] tracking-[-0.224px] text-ink"
          >
            {tool}
          </li>
        ))}
      </ul>
    </section>
  );
}
