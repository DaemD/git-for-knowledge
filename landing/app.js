(() => {
  document.documentElement.classList.add("js-ready");

  // Marketing demos always run. Windows often has "Animation effects" off,
  // which sets prefers-reduced-motion and previously killed all typing loops.
  const softenMotion = window.matchMedia(
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

  /* —— scroll reveal (never leave content invisible) —— */
  document.querySelectorAll(".section").forEach((section) => {
    [
      section.querySelector(".eyebrow"),
      section.querySelector("h2"),
      section.querySelector(".section-lede"),
    ]
      .filter(Boolean)
      .forEach((el) => el.classList.add("reveal-child"));
  });

  const revealTargets = [...document.querySelectorAll(".section, .strip, .closing, .foot")];
  revealTargets.forEach((el) => el.classList.add("reveal"));

  function markVisible(el) {
    el.classList.add("visible");
  }

  if (softenMotion) {
    revealTargets.forEach(markVisible);
  } else {
    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            markVisible(entry.target);
            revealObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.05, rootMargin: "0px 0px -4% 0px" }
    );
    revealTargets.forEach((el) => revealObserver.observe(el));
    // Failsafe: nothing stays stuck at opacity 0
    window.setTimeout(() => revealTargets.forEach(markVisible), 1200);
  }

  /* —— helpers —— */
  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function renderTyped(lines, opts = {}) {
    const { showCaret = true } = opts;
    return (
      lines
        .map((line) => {
          const cls = line.cls ? ` class="${line.cls}"` : "";
          return `<span${cls}>${escapeHtml(line.text)}</span>`;
        })
        .join("") + (showCaret ? '<span class="caret">▍</span>' : "")
    );
  }

  function inView(el, ratio = 0.1) {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    const vh = window.innerHeight || document.documentElement.clientHeight;
    return r.top < vh * (1 - ratio) && r.bottom > vh * ratio;
  }

  function loopWhileVisible(el, tick, interval) {
    let timer = null;
    let running = false;

    function step() {
      if (!running) return;
      tick();
      timer = window.setTimeout(step, interval);
    }

    function start() {
      if (running) return;
      running = true;
      step();
    }

    function stop() {
      running = false;
      if (timer) {
        window.clearTimeout(timer);
        timer = null;
      }
    }

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) start();
          else stop();
        });
      },
      { threshold: 0.08 }
    );
    io.observe(el);
    // Start immediately if already on screen (IO can miss first paint)
    if (inView(el)) start();
    window.setTimeout(() => {
      if (inView(el)) start();
    }, 100);

    return { start, stop };
  }

  /* —— Hero push → fetch (always animates) —— */
  const heroStage = document.getElementById("hero-demo");
  const heroCursor = document.getElementById("hero-cursor-body");
  const heroClaude = document.getElementById("hero-claude-body");
  const cursorPane = heroStage && heroStage.querySelector('[data-pane="cursor"]');
  const claudePane = heroStage && heroStage.querySelector('[data-pane="claude"]');

  const PUSH_LINE = "kb push";
  const PUSH_BODY = "Auth uses Postgres + Auth0.\nSessions in Redis.";
  const ACK = "[sys] ok — stored in acme-core";
  const FETCH_LINE = "kb fetch architecture postgres";
  const FETCH_BODY = "Auth uses Postgres + Auth0.\nSessions in Redis.";

  function setActivePane(which) {
    if (cursorPane) cursorPane.classList.toggle("is-hot", which === "cursor");
    if (claudePane) claudePane.classList.toggle("is-hot", which === "claude");
  }

  if (heroStage && heroCursor && heroClaude) {
    let phase = 0;
    let i = 0;

    // Seed so panes never look empty on first paint
    heroCursor.innerHTML = renderTyped([{ text: "> ", cls: "dim" }]);
    heroClaude.innerHTML = renderTyped([{ text: "> ", cls: "dim" }]);
    setActivePane("cursor");

    loopWhileVisible(
      heroStage,
      () => {
        if (phase === 0) {
          setActivePane("cursor");
          heroStage.classList.remove("is-linked");
          const text = PUSH_LINE.slice(0, i);
          heroCursor.innerHTML = renderTyped([
            { text: "> ", cls: "dim" },
            { text, cls: "hl" },
          ]);
          heroClaude.innerHTML = renderTyped([{ text: "> ", cls: "dim" }]);
          i += 1;
          if (i > PUSH_LINE.length) {
            phase = 1;
            i = 0;
          }
        } else if (phase === 1) {
          const text = PUSH_BODY.slice(0, i);
          heroCursor.innerHTML = renderTyped([
            { text: "> ", cls: "dim" },
            { text: PUSH_LINE + "\n", cls: "hl" },
            { text },
          ]);
          i += 1;
          if (i > PUSH_BODY.length) {
            phase = 2;
            i = 0;
          }
        } else if (phase === 2) {
          heroCursor.innerHTML = renderTyped(
            [
              { text: "> ", cls: "dim" },
              { text: PUSH_LINE + "\n", cls: "hl" },
              { text: PUSH_BODY + "\n" },
              { text: ACK, cls: "sys" },
            ],
            { showCaret: false }
          );
          heroStage.classList.add("is-linked");
          i += 1;
          if (i > 16) {
            phase = 3;
            i = 0;
          }
        } else if (phase === 3) {
          setActivePane("claude");
          const text = FETCH_LINE.slice(0, i);
          heroClaude.innerHTML = renderTyped([
            { text: "> ", cls: "dim" },
            { text, cls: "hl" },
          ]);
          i += 1;
          if (i > FETCH_LINE.length) {
            phase = 4;
            i = 0;
          }
        } else if (phase === 4) {
          const text = FETCH_BODY.slice(0, i);
          heroClaude.innerHTML = renderTyped([
            { text: "> ", cls: "dim" },
            { text: FETCH_LINE + "\n", cls: "hl" },
            { text },
          ]);
          i += 1;
          if (i > FETCH_BODY.length) {
            phase = 5;
            i = 0;
          }
        } else {
          heroClaude.innerHTML = renderTyped(
            [
              { text: "> ", cls: "dim" },
              { text: FETCH_LINE + "\n", cls: "hl" },
              { text: FETCH_BODY },
            ],
            { showCaret: false }
          );
          i += 1;
          if (i > 32) {
            phase = 0;
            i = 0;
            heroStage.classList.remove("is-linked");
            setActivePane("cursor");
          }
        }
      },
      36
    );
  }

  /* —— Tool strip hop —— */
  const stripTools = [...document.querySelectorAll("#strip-tools [data-tool]")];
  const stripEl = document.getElementById("strip-tools");
  if (stripTools.length && stripEl) {
    let idx = 0;
    let wait = 0;
    const activateStrip = (n) => {
      stripTools.forEach((li, i) => li.classList.toggle("is-active", i === n));
    };
    activateStrip(0);
    loopWhileVisible(
      stripEl,
      () => {
        wait += 1;
        if (wait > 18) {
          idx = (idx + 1) % stripTools.length;
          activateStrip(idx);
          wait = 0;
        }
      },
      70
    );
  }

  /* —— Amnesia wipe —— */
  const amnesia = document.getElementById("amnesia-demo");
  const amnesiaPanes = [...document.querySelectorAll(".amnesia-pane")];

  if (amnesia && amnesiaPanes.length) {
    let phase = 0;
    let wait = 0;

    function amnesiaReset() {
      amnesiaPanes.forEach((p) => {
        p.classList.remove("is-wiping", "is-cleared");
      });
    }

    amnesiaReset();

    loopWhileVisible(
      amnesia,
      () => {
        if (phase === 0) {
          amnesiaReset();
          wait += 1;
          if (wait > 18) {
            phase = 1;
            wait = 0;
          }
        } else if (phase >= 1 && phase <= 3) {
          const pane = amnesiaPanes[phase - 1];
          if (wait === 0) pane.classList.add("is-wiping");
          wait += 1;
          if (wait === 7) {
            pane.classList.remove("is-wiping");
            pane.classList.add("is-cleared");
          }
          if (wait > 11) {
            phase += 1;
            wait = 0;
          }
        } else if (phase === 4) {
          wait += 1;
          if (wait > 22) {
            phase = 5;
            wait = 0;
          }
        } else {
          amnesiaReset();
          wait += 1;
          if (wait > 8) {
            phase = 0;
            wait = 0;
          }
        }
      },
      60
    );
  }

  /* —— Examples typewriter —— */
  const EXAMPLES = [
    `kb push """
Session summary (Cursor, auth refactor):
- Auth0 + Google social only
- Callbacks: localhost + Claude
- Rejected: rolling our own JWT
"""

kb fetch What did we decide about auth?`,
    `kb push """
ChatGPT research — competitor memory:
- Mem0: strong SDK, weaker shared KB
- Wedge: shared kb_id + Google invite
- Pricing: free solo, paid seats
"""

kb fetch What's our wedge vs Mem0?`,
    `kb create acme-rebrand "Acme Q2"

kb push """
Claude design review — Acme Q2:
Must: custom CSS only, WCAG AA
Deploy: Vercel preview URLs
Tone: quiet, technical
"""

kb fetch What CSS constraints does Acme have?`,
  ];

  const exTabs = [...document.querySelectorAll(".example-tab")];
  const exPanels = [...document.querySelectorAll(".example-panel")];
  const exLive = document.getElementById("example-live");
  let exIndex = 0;
  let exChar = 0;
  let exHold = 0;
  let exDone = false;
  let exRunning = null;

  function paintExample(index, text, showCaret) {
    const body = document.querySelector(`[data-ex-body="${index}"]`);
    if (!body) return;
    const escaped = escapeHtml(text);
    const highlighted = escaped
      .replace(/\bkb push\b/g, '<span class="hl">kb push</span>')
      .replace(/\bkb fetch\b/g, '<span class="hl">kb fetch</span>')
      .replace(/\bkb create\b/g, '<span class="hl">kb create</span>');
    body.innerHTML =
      highlighted + (showCaret ? '<span class="caret">▍</span>' : "");
  }

  function showExamplePanel(index) {
    exIndex = index;
    exTabs.forEach((tab) => {
      const on = Number(tab.dataset.ex) === index;
      tab.classList.toggle("active", on);
      tab.setAttribute("aria-selected", on ? "true" : "false");
    });
    exPanels.forEach((panel) => {
      panel.classList.toggle(
        "active",
        Number(panel.dataset.exPanel) === index
      );
    });
  }

  function resetExampleTyping(index) {
    exChar = 0;
    exHold = 0;
    exDone = false;
    showExamplePanel(index);
    paintExample(index, "", true);
  }

  function tickExample() {
    const full = EXAMPLES[exIndex];
    if (!exDone) {
      exChar = Math.min(full.length, exChar + 3);
      paintExample(exIndex, full.slice(0, exChar), true);
      if (exChar >= full.length) {
        paintExample(exIndex, full, false);
        exDone = true;
        exHold = 0;
      }
    } else {
      exHold += 1;
      if (exHold > 40) {
        resetExampleTyping((exIndex + 1) % EXAMPLES.length);
      }
    }
  }

  exTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      resetExampleTyping(Number(tab.dataset.ex));
    });
  });

  if (exLive) {
    EXAMPLES.forEach((_, i) => paintExample(i, "", false));
    resetExampleTyping(0);
    exRunning = loopWhileVisible(exLive, tickExample, 24);
  }
})();
