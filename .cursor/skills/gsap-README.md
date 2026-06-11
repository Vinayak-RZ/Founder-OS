# GSAP skills (Founder OS)

Project-local copies of the official Cursor GSAP plugin skills:

- `gsap-core` — tweens, easing, `gsap.matchMedia()`, reduced motion
- `gsap-scrolltrigger` — scroll-linked animations, batch, pinning
- `gsap-timeline` — sequencing
- `gsap-performance` — transform-first, jank avoidance

**Runtime:** GSAP 3.12.7 + ScrollTrigger via CDN in `dashboard/static/index.html`.

**App integration:** `dashboard/static/motion.js` (`FOSMotion`) — view transitions, hero staggers, ScrollTrigger batch on cards, chat message entrances. Uses `gsap.context()` per view with `revert()` on navigation (vanilla SPA pattern).
