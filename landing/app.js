(() => {
  const reduceMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  /* —— tabs / copy (existing) —— */
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

  /* —— scroll reveal + stagger —— */
  document.querySelectorAll(".section").forEach((section) => {
    [
      section.querySelector(".eyebrow"),
      section.querySelector("h2"),
      section.querySelector(".section-lede"),
    ]
      .filter(Boolean)
      .forEach((el) => el.classList.add("reveal-child"));
  });

  const revealTargets = document.querySelectorAll(
    ".section, .strip, .closing, .foot"
  );
  revealTargets.forEach((el) => el.classList.add("reveal"));

  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
  );
  revealTargets.forEach((el) => revealObserver.observe(el));

  /* —— DemoLoop helper —— */
  function createDemoLoop(el, tickFn, { interval = 80 } = {}) {
    let timer = null;
    let running = false;
    let state = { t: 0 };

    function step() {
      if (!running) return;
      state = tickFn(state) || state;
      timer = window.setTimeout(step, interval);
    }

    function start() {
      if (running || reduceMotion) return;
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

    function reset(next) {
      state = next || { t: 0 };
    }

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) start();
          else stop();
        });
      },
      { threshold: 0.2 }
    );
    io.observe(el);

    return { start, stop, reset, getState: () => state, setState: (s) => (state = s) };
  }

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

  /* —— Hero push → fetch —— */
  const heroStage = document.getElementById("hero-demo");
  const heroCursor = document.getElementById("hero-cursor-body");
  const heroClaude = document.getElementById("hero-claude-body");

  const PUSH_LINE = "kb push";
  const PUSH_BODY =
    "Auth uses Postgres + Auth0.\nSessions in Redis.";
  const ACK = "[sys] ok — stored in acme-core";
  const FETCH_LINE = "kb fetch architecture postgres";
  const FETCH_BODY = "Auth uses Postgres + Auth0.\nSessions in Redis.";

  function heroStaticFrame() {
    if (!heroCursor || !heroClaude || !heroStage) return;
    heroStage.classList.add("is-linked");
    heroCursor.innerHTML = renderTyped(
      [
        { text: "> ", cls: "dim" },
        { text: PUSH_LINE + "\n", cls: "hl" },
        { text: PUSH_BODY + "\n" },
        { text: ACK, cls: "sys" },
      ],
      { showCaret: false }
    );
    heroClaude.innerHTML = renderTyped(
      [
        { text: "> ", cls: "dim" },
        { text: FETCH_LINE + "\n", cls: "hl" },
        { text: FETCH_BODY },
      ],
      { showCaret: false }
    );
  }

  if (heroStage && heroCursor && heroClaude) {
    if (reduceMotion) {
      heroStaticFrame();
    } else {
      createDemoLoop(
        heroStage,
        (state) => {
          let { phase = 0, i = 0 } = state;
          const phases = [
            // 0 type push cmd
            () => {
              const text = PUSH_LINE.slice(0, i);
              heroCursor.innerHTML = renderTyped([
                { text: "> ", cls: "dim" },
                { text, cls: "hl" },
              ]);
              heroClaude.innerHTML = renderTyped([{ text: "> ", cls: "dim" }]);
              heroStage.classList.remove("is-linked");
              i += 1;
              if (i > PUSH_LINE.length) {
                phase = 1;
                i = 0;
              }
              return { phase, i };
            },
            // 1 type push body
            () => {
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
              return { phase, i };
            },
            // 2 show ack + hold
            () => {
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
              if (i > 18) {
                phase = 3;
                i = 0;
              }
              return { phase, i };
            },
            // 3 type fetch
            () => {
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
              return { phase, i };
            },
            // 4 type fetch body
            () => {
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
              return { phase, i };
            },
            // 5 hold then reset
            () => {
              heroClaude.innerHTML = renderTyped(
                [
                  { text: "> ", cls: "dim" },
                  { text: FETCH_LINE + "\n", cls: "hl" },
                  { text: FETCH_BODY },
                ],
                { showCaret: false }
              );
              i += 1;
              if (i > 28) {
                phase = 0;
                i = 0;
                heroStage.classList.remove("is-linked");
              }
              return { phase, i };
            },
          ];
          return phases[phase]();
        },
        { interval: 42 }
      );
    }
  }

  /* —— Tool strip hop —— */
  const stripTools = [...document.querySelectorAll("#strip-tools [data-tool]")];
  if (stripTools.length) {
    let idx = 0;
    const activateStrip = (n) => {
      stripTools.forEach((li, i) => li.classList.toggle("is-active", i === n));
    };
    activateStrip(0);
    if (!reduceMotion) {
      const stripEl = document.getElementById("strip-tools");
      createDemoLoop(
        stripEl,
        (state) => {
          let { wait = 0 } = state;
          wait += 1;
          if (wait > 22) {
            idx = (idx + 1) % stripTools.length;
            activateStrip(idx);
            wait = 0;
          }
          return { wait };
        },
        { interval: 80 }
      );
    } else {
      stripTools.forEach((li) => li.classList.add("is-active"));
    }
  }

  /* —— Amnesia wipe —— */
  const amnesia = document.getElementById("amnesia-demo");
  const amnesiaPanes = [...document.querySelectorAll(".amnesia-pane")];

  function amnesiaReset() {
    amnesiaPanes.forEach((p) => {
      p.classList.remove("is-wiping", "is-cleared");
    });
  }

  function amnesiaStaticCleared() {
    amnesiaPanes.forEach((p) => {
      p.classList.add("is-cleared");
      p.classList.remove("is-wiping");
    });
  }

  if (amnesia && amnesiaPanes.length) {
    if (reduceMotion) {
      amnesiaStaticCleared();
    } else {
      createDemoLoop(
        amnesia,
        (state) => {
          let { phase = 0, wait = 0 } = state;
          // 0 show text, 1 wipe 0, 2 wipe 1, 3 wipe 2, 4 hold cleared, 5 reset
          if (phase === 0) {
            amnesiaReset();
            wait += 1;
            if (wait > 20) return { phase: 1, wait: 0 };
          } else if (phase >= 1 && phase <= 3) {
            const pane = amnesiaPanes[phase - 1];
            if (wait === 0) pane.classList.add("is-wiping");
            wait += 1;
            if (wait === 8) {
              pane.classList.remove("is-wiping");
              pane.classList.add("is-cleared");
            }
            if (wait > 12) return { phase: phase + 1, wait: 0 };
          } else if (phase === 4) {
            wait += 1;
            if (wait > 24) return { phase: 5, wait: 0 };
          } else {
            amnesiaReset();
            wait += 1;
            if (wait > 10) return { phase: 0, wait: 0 };
          }
          return { phase, wait };
        },
        { interval: 70 }
      );
    }
  }

  /* —— Examples live typewriter —— */
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
  let exTimer = null;
  let exVisible = false;
  let exChar = 0;
  let exHold = 0;
  let exDone = false;

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
    if (reduceMotion) {
      paintExample(index, EXAMPLES[index], false);
      return;
    }
    paintExample(index, "", true);
  }

  function tickExample() {
    if (!exVisible || reduceMotion) return;
    const full = EXAMPLES[exIndex];
    if (!exDone) {
      exChar = Math.min(full.length, exChar + 2);
      paintExample(exIndex, full.slice(0, exChar), true);
      if (exChar >= full.length) {
        paintExample(exIndex, full, false);
        exDone = true;
        exHold = 0;
      }
    } else {
      exHold += 1;
      if (exHold > 50) {
        resetExampleTyping((exIndex + 1) % EXAMPLES.length);
      }
    }
    exTimer = window.setTimeout(tickExample, 28);
  }

  function startExampleLoop() {
    if (exTimer || reduceMotion) return;
    tickExample();
  }

  function stopExampleLoop() {
    if (exTimer) {
      window.clearTimeout(exTimer);
      exTimer = null;
    }
  }

  exTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      stopExampleLoop();
      resetExampleTyping(Number(tab.dataset.ex));
      if (exVisible) startExampleLoop();
    });
  });

  if (exLive) {
    EXAMPLES.forEach((text, i) => {
      paintExample(i, reduceMotion ? text : "", false);
    });
    resetExampleTyping(0);

    const exIo = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          exVisible = entry.isIntersecting;
          if (exVisible) {
            if (!exDone && exChar === 0) resetExampleTyping(exIndex);
            startExampleLoop();
          } else {
            stopExampleLoop();
          }
        });
      },
      { threshold: 0.2 }
    );
    exIo.observe(exLive);
  }
})();
