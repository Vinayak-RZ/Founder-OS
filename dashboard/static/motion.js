/* Founder OS motion — GSAP + ScrollTrigger (Forge Industrial / HIW patterns) */
window.FOSMotion = (function () {
  let viewCtx = null;
  let shellCtx = null;
  let mm = null;
  let liveTween = null;

  const EASE_ENTER = "power2.out";
  const EASE_DRAW = "power2.inOut";

  function ready() {
    return typeof gsap !== "undefined";
  }

  function reducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function init() {
    if (!ready()) return false;
    if (typeof ScrollTrigger !== "undefined") {
      gsap.registerPlugin(ScrollTrigger);
    }
    gsap.defaults({ ease: EASE_ENTER, duration: 0.55 });
    mm = gsap.matchMedia();
    return true;
  }

  function ensureContentVisible(root) {
    const el = root || document.getElementById("content");
    if (!el) return;
    el.querySelectorAll(".driver-card, .agent-card, .command-header, .dashboard-grid, .chat-wrap").forEach((node) => {
      node.style.visibility = "visible";
      node.style.opacity = "";
    });
    if (ready()) gsap.set(el.querySelectorAll("[style*='opacity']"), { clearProps: "opacity,visibility" });
  }

  function revertView() {
    viewCtx?.revert();
    viewCtx = null;
    ensureContentVisible();
  }

  function revertShell() {
    shellCtx?.revert();
    shellCtx = null;
  }

  function runShell() {
    if (!ready() || reducedMotion()) return;
    revertShell();
    const app = document.querySelector(".app");
    if (!app) return;

    shellCtx = gsap.context(() => {
      gsap.from(".brand-mark", {
        scale: 0.6,
        autoAlpha: 0,
        duration: 0.5,
        ease: "back.out(1.6)",
      });
      gsap.from(".brand-name, .brand-sub", {
        autoAlpha: 0,
        x: -10,
        duration: 0.45,
        stagger: 0.06,
        delay: 0.08,
      });
      gsap.from(".nav-link", {
        autoAlpha: 0,
        x: -16,
        duration: 0.4,
        stagger: 0.03,
        delay: 0.12,
      });
      gsap.from(".topbar", {
        autoAlpha: 0,
        y: -8,
        duration: 0.45,
        delay: 0.05,
      });
    }, app);
  }

  function animateTopbarTitle() {
    if (!ready() || reducedMotion()) return;
    const el = document.getElementById("view-title");
    if (!el) return;
    gsap.fromTo(
      el,
      { autoAlpha: 0, y: 10 },
      { autoAlpha: 1, y: 0, duration: 0.38, ease: EASE_ENTER, overwrite: true }
    );
  }

  function pulseLiveStrip(active) {
    if (!ready() || reducedMotion()) return;
    const strip = document.getElementById("live-strip");
    if (!strip) return;
    liveTween?.kill();
    if (active) {
      strip.hidden = false;
      liveTween = gsap.fromTo(
        strip,
        { autoAlpha: 0, x: -8 },
        { autoAlpha: 1, x: 0, duration: 0.35, ease: EASE_ENTER }
      );
    } else {
      liveTween = gsap.to(strip, {
        autoAlpha: 0,
        duration: 0.2,
        onComplete: () => { strip.hidden = true; },
      });
    }
  }

  function heroSequence(root, tl, at = 0) {
    const hero = root.querySelector(".hero-band-cinema, .worlds-hero");
    if (!hero) return at;
    const lead = hero.querySelectorAll(
      ".caption-uppercase, .section-eyebrow, .hero-title, .hero-band-cinema h2, .worlds-hero-lead h2, .worlds-hero-lead p, .hero-actions button, .hero-band-cinema p"
    );
    if (lead.length) {
      tl.from(lead, { autoAlpha: 0, y: 28, duration: 0.85, stagger: 0.07, ease: EASE_ENTER }, at);
    }
    const stats = hero.querySelectorAll(".worlds-stat, .spec-cell");
    if (stats.length) {
      tl.from(stats, { autoAlpha: 0, y: 18, duration: 0.6, stagger: 0.06, ease: EASE_ENTER }, at + 0.12);
    }
    return at + 0.35;
  }

  function worldsSequence(root, tl, at = 0) {
    const panels = root.querySelectorAll(".worlds-panel");
    if (!panels.length) return at;
    tl.from(panels, { autoAlpha: 0, y: 32, duration: 0.7, stagger: 0.1, ease: EASE_ENTER }, at);
    const treeItems = root.querySelectorAll(".world-tree-item");
    if (treeItems.length) {
      tl.from(treeItems, { autoAlpha: 0, x: -14, duration: 0.44, stagger: 0.05, ease: EASE_ENTER }, at + 0.08);
    }
    const graph = root.querySelector("#graph-world");
    if (graph) {
      tl.from(graph, { autoAlpha: 0, scale: 0.98, duration: 0.65, ease: EASE_DRAW }, at + 0.15);
    }
    const drawer = root.querySelector(".world-create-drawer");
    if (drawer) {
      tl.from(drawer, { autoAlpha: 0, y: 16, duration: 0.5 }, at + 0.22);
    }
    return at + 0.4;
  }

  function cardsInView(root) {
    if (typeof ScrollTrigger === "undefined" || !root) return;
    const scroller = document.getElementById("main-content");
    const targets = root.querySelectorAll(".memory-collection, .trace-card");
    if (!targets.length) return;
    ScrollTrigger.batch(targets, {
      scroller: scroller || undefined,
      start: "top 92%",
      once: true,
      onEnter: (batch) => {
        gsap.fromTo(
          batch,
          { autoAlpha: 0, y: 16 },
          {
            autoAlpha: 1,
            y: 0,
            duration: 0.45,
            stagger: 0.05,
            ease: EASE_ENTER,
            overwrite: "auto",
            clearProps: "opacity,visibility,transform",
          }
        );
      },
    });
  }

  function runView(viewName) {
    revertView();
    const root = document.getElementById("content");
    if (!root) return;
    if (!ready() || reducedMotion()) {
      ensureContentVisible(root);
      return;
    }

    viewCtx = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: EASE_ENTER } });
      let t = 0;

      t = heroSequence(root, tl, t);

      if (viewName === "world") {
        t = worldsSequence(root, tl, t);
      } else if (viewName === "agents") {
        const cards = root.querySelectorAll(".agent-card");
        if (cards.length) {
          tl.fromTo(
            cards,
            { autoAlpha: 0, y: 20 },
            { autoAlpha: 1, y: 0, duration: 0.5, stagger: 0.05, clearProps: "opacity,visibility,transform" },
            t
          );
        }
        const panel = root.querySelector(".delegate-panel");
        if (panel) {
          tl.fromTo(
            panel,
            { autoAlpha: 0, x: 16 },
            { autoAlpha: 1, x: 0, duration: 0.45, clearProps: "opacity,visibility,transform" },
            t + 0.08
          );
        }
        cardsInView(root);
      } else if (viewName === "chat") {
        const wrap = root.querySelector(".chat-wrap");
        if (wrap) {
          tl.fromTo(
            wrap,
            { autoAlpha: 0, y: 12 },
            { autoAlpha: 1, y: 0, duration: 0.4, clearProps: "opacity,visibility,transform" },
            t
          );
        }
        const live = root.querySelector(".live-panel");
        if (live) {
          tl.fromTo(
            live,
            { autoAlpha: 0, x: 12 },
            { autoAlpha: 1, x: 0, duration: 0.4, clearProps: "opacity,visibility,transform" },
            t + 0.06
          );
        }
      } else if (viewName === "dashboard") {
        const grid = root.querySelectorAll(".dashboard-grid .driver-card");
        if (grid.length) {
          tl.fromTo(
            grid,
            { autoAlpha: 0, y: 20 },
            {
              autoAlpha: 1,
              y: 0,
              duration: 0.5,
              stagger: 0.04,
              clearProps: "opacity,visibility,transform",
            },
            t + 0.08
          );
        }
      } else {
        cardsInView(root);
      }

      if (typeof ScrollTrigger !== "undefined") {
        requestAnimationFrame(() => ScrollTrigger.refresh());
      }
      tl.eventCallback("onComplete", () => ensureContentVisible(root));
    }, root);
    gsap.delayedCall(1.2, () => ensureContentVisible(root));
  }

  function flashElement(el) {
    if (!ready() || reducedMotion() || !el) return;
    gsap.fromTo(
      el,
      { boxShadow: "0 0 0 0 color-mix(in srgb, var(--color-primary) 45%, transparent)" },
      {
        boxShadow: "0 0 0 6px color-mix(in srgb, var(--color-primary) 0%, transparent)",
        duration: 0.55,
        ease: EASE_ENTER,
      }
    );
  }

  function animateNewMessage(el) {
    if (!ready() || reducedMotion() || !el) return;
    gsap.from(el, { autoAlpha: 0, y: 12, duration: 0.35, ease: EASE_ENTER });
  }

  return {
    init,
    runShell,
    runView,
    revertView,
    ensureContentVisible,
    animateTopbarTitle,
    pulseLiveStrip,
    flashElement,
    animateNewMessage,
  };
})();
