const TOOLS = ["Cursor", "Antigravity", "Claude Code", "Claude", "ChatGPT"];

export function ToolsStrip() {
  return (
    <section className="bg-canvas py-16">
      <p className="mb-7 text-center text-[13px] tracking-[-0.39px] text-ink-mute">
        One memory layer across the tools you already pay for
      </p>
      <ul className="mx-auto flex max-w-3xl flex-wrap items-center justify-center gap-2 px-4">
        {TOOLS.map((tool) => (
          <li
            key={tool}
            className="rounded-[60px] border border-hairline bg-surface-1 px-3 py-1 text-[12px] font-normal tracking-[0.24px] text-ink-muted"
          >
            {tool}
          </li>
        ))}
      </ul>
    </section>
  );
}
