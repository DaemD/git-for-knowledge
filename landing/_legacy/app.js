(() => {
  const reduceMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  /* —— tabs / copy —— */
  const tabs = [...document.querySelectorAll(".tab")];
  const panels = [...document.querySelectorAll(".panel")];

  function activate(client) {
    tabs.forEach((tab) => {
      const on = tab.dataset.client === client;
      tab.classList.toggle("active", on);
      tab.setAttribute("aria-selected", on ? "true" : "false");
    });
    panels.forEach((panel) => {
      panel.classList.toggle("active", panel.dataset.panel === client);
    });
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => activate(tab.dataset.client));
  });

  document.querySelectorAll(".copy").forEach((button) => {
    button.addEventListener("click", async () => {
      const id = button.dataset.copy;
      const code = document.getElementById(`snippet-${id}`);
      if (!code) return;
      try {
        await navigator.clipboard.writeText(code.textContent);
        const previous = button.textContent;
        button.textContent = "Copied";
        button.classList.add("copied");
        window.setTimeout(() => {
          button.textContent = previous;
          button.classList.remove("copied");
        }, 1400);
      } catch {
        button.textContent = "Select & copy";
      }
    });
  });

  /* —— scroll reveal —— */
  const revealTargets = document.querySelectorAll(
    ".section, .strip, .closing, .foot, .cta-band"
  );
  if (reduceMotion) {
    revealTargets.forEach((el) => el.classList.add("visible"));
  } else {
    revealTargets.forEach((el) => el.classList.add("reveal"));
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
    );
    revealTargets.forEach((el) => observer.observe(el));
  }

  /* —— helpers —— */
  function sleep(ms, signal) {
    return new Promise((resolve, reject) => {
      if (signal?.aborted) {
        reject(new DOMException("Aborted", "AbortError"));
        return;
      }
      const id = window.setTimeout(resolve, ms);
      signal?.addEventListener(
        "abort",
        () => {
          window.clearTimeout(id);
          reject(new DOMException("Aborted", "AbortError"));
        },
        { once: true }
      );
    });
  }

  async function typeInto(el, htmlChunks, signal, charDelay = 18, append = false) {
    if (!append) el.innerHTML = "";
    for (const chunk of htmlChunks) {
      if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
      if (chunk.html) {
        el.insertAdjacentHTML("beforeend", chunk.html);
        continue;
      }
      const text = chunk.text ?? "";
      for (let i = 0; i < text.length; i += 1) {
        if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
        el.insertAdjacentText("beforeend", text[i]);
        await sleep(charDelay, signal);
      }
    }
  }

  function withCaret(el) {
    const caret = document.createElement("span");
    caret.className = "caret";
    caret.textContent = "▍";
    el.appendChild(caret);
    return () => caret.remove();
  }

  /* —— push / fetch hero demo —— */
  const PUSH_LINES = [
    { html: '<span class="dim">&gt; </span>' },
    { text: "kb push" },
    { html: "\n" },
    {
      text: "Auth uses Postgres + Auth0. Sessions in Redis. Prefer soft deletes.",
    },
    { html: "\n" },
    { html: '<span class="ok">ok — stored in acme-core</span>' },
  ];
  const FETCH_LINES = [
    { html: '<span class="dim">&gt; </span>' },
    { text: "kb fetch architecture postgres" },
    { html: "\n" },
    {
      text: "Auth uses Postgres + Auth0. Sessions in Redis. Prefer soft deletes.",
    },
  ];
  const STATIC_CURSOR =
    '<span class="dim">&gt; </span>kb push\nAuth uses Postgres + Auth0. Sessions in Redis. Prefer soft deletes.\n<span class="ok">ok — stored in acme-core</span>';
  const STATIC_CLAUDE =
    '<span class="dim">&gt; </span>kb fetch architecture postgres\nAuth uses Postgres + Auth0. Sessions in Redis. Prefer soft deletes.';

  async function runPushFetch(root, signal) {
    const cursor = root.querySelector("#demo-cursor");
    const claude = root.querySelector("#demo-claude");
    if (!cursor || !claude) return;

    if (reduceMotion) {
      cursor.innerHTML = STATIC_CURSOR;
      claude.innerHTML = STATIC_CLAUDE;
      return;
    }

    while (!signal.aborted) {
      cursor.innerHTML = "";
      claude.innerHTML = "";
      let removeCaret = withCaret(cursor);
      try {
        removeCaret();
        await typeInto(cursor, PUSH_LINES.slice(0, 4), signal, 16);
        removeCaret = withCaret(cursor);
        await sleep(400, signal);
        removeCaret();
        await typeInto(cursor, PUSH_LINES.slice(4), signal, 12, true);
        await sleep(700, signal);

        removeCaret = withCaret(claude);
        removeCaret();
        await typeInto(claude, FETCH_LINES, signal, 16);
        await sleep(2200, signal);
      } catch (err) {
        if (err.name === "AbortError") return;
        throw err;
      }
    }
  }

  /* —— tools strip hop —— */
  function runStrip(root, signal) {
    const items = [...root.querySelectorAll("li")];
    if (!items.length) return;
    if (reduceMotion) {
      items[0]?.classList.add("is-active");
      return;
    }
    let i = 0;
    const tick = () => {
      if (signal.aborted) return;
      items.forEach((el, idx) => el.classList.toggle("is-active", idx === i));
      i = (i + 1) % items.length;
    };
    tick();
    const id = window.setInterval(tick, 1400);
    signal.addEventListener("abort", () => window.clearInterval(id), {
      once: true,
    });
  }

  /* —— amnesia wipe —— */
  async function runAmnesia(root, signal) {
    const panes = [...root.querySelectorAll(".amnesia-pane")];
    if (!panes.length) return;
    if (reduceMotion) {
      panes.forEach((p) => p.classList.add("is-wiped"));
      return;
    }
    while (!signal.aborted) {
      panes.forEach((p) => p.classList.remove("is-wiped"));
      try {
        await sleep(900, signal);
        for (const pane of panes) {
          pane.classList.add("is-wiped");
          await sleep(380, signal);
        }
        await sleep(1600, signal);
      } catch (err) {
        if (err.name === "AbortError") return;
        throw err;
      }
    }
  }

  /* —— DemoLoop: start/stop on visibility —— */
  const controllers = new WeakMap();

  function startDemo(el) {
    stopDemo(el);
    const ac = new AbortController();
    controllers.set(el, ac);
    const kind = el.dataset.demo;
    if (kind === "push-fetch") runPushFetch(el, ac.signal);
    else if (kind === "strip") runStrip(el, ac.signal);
    else if (kind === "amnesia") runAmnesia(el, ac.signal);
  }

  function stopDemo(el) {
    const ac = controllers.get(el);
    if (ac) {
      ac.abort();
      controllers.delete(el);
    }
  }

  const demoRoots = document.querySelectorAll("[data-demo]");
  if (reduceMotion) {
    demoRoots.forEach((el) => startDemo(el));
  } else {
    const demoObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) startDemo(entry.target);
          else stopDemo(entry.target);
        });
      },
      { threshold: 0.25 }
    );
    demoRoots.forEach((el) => demoObserver.observe(el));
  }
})();
