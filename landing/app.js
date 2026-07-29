(() => {
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

  const revealTargets = document.querySelectorAll(
    ".section, .strip, .closing, .foot"
  );
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
})();
