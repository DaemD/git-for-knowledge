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
            className="rounded-full bg-primary-bg-subdued-hover px-2 py-1 text-[10px] font-normal uppercase tracking-[0.1px] text-primary-deep"
          >
            {tool}
          </li>
        ))}
      </ul>
    </section>
  );
}
