# How It Works — Page Design Dock

**Route:** `/how-it-works`  
**Last synced:** June 2026 (implementation on `main`)  
**Parent system:** Forge Industrial v2.0 — see `Deisgn_Stamped_Energy_original.md` and `styles/theme.css`  
**Content source:** `lib/content/howItWorks.ts`  
**Component root:** `components/how-it-works/`

This document captures the **full visual, structural, and motion essence** of the How It Works page as built — colors, typography, spacing, section rhythm, diagram language, and animation contracts. Use it when extending the page, swapping media, or briefing designers and engineers.

---

## 1. Page purpose & narrative

### What this page is
A **prescriptive intelligence story** for Indian SME manufacturers: unified plant data → contextual analysis → prescriptions → floor execution → verified ₹ savings. It is diagram-first, scroll-driven, and intentionally **not** a wall of marketing copy.

### Narrative arc (top → bottom)
1. **Hook** — What Stamped is, in one sentence + interactive plant SLD.
2. **Workflow loop** — Five steps (Connect → Verify) as a pinned scroll journey.
3. **Intelligence layer** — Four-step horizontal/vertical stack (Monitor → Track).
4. **Product preview** — Prescription dashboard embed slot.
5. **Core capabilities** — Four animated platform cards on a dark anchor band.
6. **Before vs With Stamped** — Emotional contrast, 1×4 vertical lists.
7. **Deployment path** — Timeline to live savings.
8. **Final CTA** — Discovery call on dark band.

### Tone
- **Industrial minimalism** — crisp borders, warm greys, coral accents; no soft consumer fluff.
- **Operational credibility** — Modbus, SCADA, M&V, ₹, shift-aware language.
- **Prescriptive, not passive** — “Prescriptions, not charts”; actions reach the floor.

---

## 2. Section map & backgrounds

The page alternates **light bands** (`surface`, `surface-low`) with **dark anchor bands** (`secondary` / deep forest).

| # | Section | Component | Background | Text mode |
|---|---------|-----------|------------|-----------|
| 1 | Opening + Plant SLD | `HiwOpening` | `bg-surface` + primary radial glow | Light |
| 2 | Workflow loop (pinned) | `HiwPinnedJourney` | `bg-surface-low` | Light |
| 3 | Intelligence layer | `HiwIntelligenceStack` | `bg-secondary` | Dark (`on-secondary`) |
| 4 | Prescription dashboard | `HiwPrescriptionWalkthrough` | `bg-surface-low` | Light |
| 5 | Core capabilities | `HiwCapabilities` | `bg-secondary` | Dark |
| 6 | Before vs With Stamped | `HiwBeforeAfter` | `bg-surface-low` | Light |
| 7 | Deployment path | `HiwDeployment` | `bg-surface-low` | Light |
| 8 | Final CTA | `HiwPageCta` | `bg-secondary` | Dark |

### Vertical padding rhythm
- **Major sections:** `py-20 md:py-28` (80px / 112px)
- **Capabilities:** `py-[3.6rem] md:py-[5.4rem]` (slightly tighter dark band)
- **Opening:** `pt-28 md:pt-32`, `pb-14 md:pb-20` (accounts for site header)
- **Pinned journey header:** `pt-16 pb-6 md:pt-20 md:pb-8` inside `surface-low`

---

## 3. Color system (page usage)

All colors resolve to CSS variables in `styles/theme.css`. Tailwind utilities map via `app/globals.css`.

### 3.1 Full palette reference

| Token | Hex | Role on HIW page |
|-------|-----|------------------|
| **Primary** | `#F75440` | CTAs, eyebrows, active states, diagram strokes, savings emphasis |
| **On-primary** | `#ffffff` | Text on primary buttons, check badges |
| **Inverse-primary** | `#ffb4a8` | Eyebrows on dark sections, stack arrows, glow accents |
| **Primary / opacity** | `primary/5` – `primary/45` | Active nav cards, chips, callouts, gradients |
| **Secondary** | `#051F13` | Dark section backgrounds (capabilities, intelligence, CTA) |
| **On-secondary** | `#ffffff` | Headlines on dark bands |
| **On-secondary / 80–90** | — | Body copy on dark bands |
| **Inverse-surface** | `#2d312e` | Capability & stack card fills (`inverse-surface/50`) |
| **Surface** | `#f7faf5` | Opening hero background |
| **Surface-low** | `#f1f4f0` | Default light section fill |
| **Surface-lowest** | `#ffffff` | Cards, diagram canvases, node boxes |
| **Surface-dim** | `#d8dbd6` | “Before” card header / item wells |
| **On-surface** | `#191c1a` | Primary body text |
| **On-surface-variant** | `#5a403c` | Secondary text, hints |
| **Outline-variant** | `#e3beb8` | Borders (warm pink-grey) |
| **Outline** | `#8f706b` | Stronger border accents |
| **Tertiary** | `#00666b` | Execute diagram “In Progress” status dot |
| **Error** | `#ba1a1a` | Reserved; not used on HIW currently |

### 3.2 Section-specific color recipes

**Opening hero glow**
```css
radial-gradient(circle at 50% 0%, color-mix(in srgb, var(--brand-primary) 12%, transparent), transparent 60%)
```

**Plant SLD canvas**
- Fill: `surface-lowest`
- Grid: primary at 8% opacity, 40×40px
- Lines: `var(--brand-primary)`, stroke-opacity 0.45, dash `6 5`
- Hub node: `border-2 border-primary`, glow circle `fillOpacity 0.08`

**Dark band cards** (capabilities, intelligence stack)
- Card: `border-on-secondary/15 bg-inverse-surface/50 backdrop-blur-sm`
- Hover shadow: `0_20px_48px_-28px color-mix(primary 45%, transparent)`

**Capability visual panels**
- Always `bg-surface-lowest` (white) inside dark cards — deliberate **light inset** for diagram readability

**Before card**
- Header: `bg-surface-dim/60`, subtitle “Reactive · fragmented”
- Items: `bg-surface-dim/40`, ✕ in `outline-variant/30` circle

**With Stamped card**
- Border: `border-2 border-primary/35`
- Background gradient: `160deg`, primary 10% → `surface-container-lowest`
- Shadow: primary 50% at 30% blur
- Header: `bg-primary/10`, subtitle in `text-primary`
- Items: `bg-primary/8`, ✓ in solid `bg-primary` circle

**Diagram shell** (workflow loop)
- Outer: `border-outline-variant/50 bg-surface-lowest`
- Inner stage: `border-outline-variant/40 bg-surface-low/60`
- Eyebrow: `text-primary uppercase tracking-[0.12em]`

---

## 4. Typography

### Font families
| Use | Family | Tailwind |
|-----|--------|----------|
| Headlines, step numbers | Plus Jakarta Sans | `font-display` |
| Body, labels, chips | Inter | default sans |

### Scale & patterns on this page

| Element | Classes / size | Weight |
|---------|----------------|--------|
| Page H1 (opening) | `text-3xl md:text-4xl lg:text-[2.5rem]` | extrabold |
| Section H2 | `text-3xl md:text-4xl` via `SectionHeading` | bold |
| Section eyebrow | `text-xs uppercase tracking-[0.14em]` | semibold |
| Opening eyebrow | `tracking-[0.16em]` | semibold |
| Journey step number | `font-display text-2xl` | extrabold, `text-primary` |
| Journey step title | `text-base` / panel `text-2xl md:text-3xl` | bold |
| Journey tagline | `text-sm` | medium |
| Journey chips | `rounded-full text-xs md:text-sm` | medium |
| Capability title | `text-lg md:text-xl` | bold |
| Capability body | `text-sm md:text-[15px] leading-6/7` | regular |
| Diagram eyebrow | `text-xs uppercase tracking-[0.12em]` | semibold |
| Diagram microcopy | `text-[10px]` – `text-[11px]` | semibold / regular |
| Stack layer subtitle | `text-[10px] uppercase tracking-[0.14em]` | semibold, `inverse-primary` |
| Deployment week | `text-xs uppercase tracking-[0.12em]` | semibold, primary |

### Copy conventions
- **₹** always for Indian currency impact
- **En-dash** in ranges: `Week 1–2`, `Open → Done`
- **Middle dot** for lists: `Modbus · OPC-UA · MQTT`
- **Before vs With Stamped** — capital W, no period after “vs”

---

## 5. Layout & grid

### Container
Shared `Container` — max-width aligned with site grid (12-col, 1440px cap).

### Pinned workflow (desktop ≥1024px)
- **12-column grid:** step nav `col-span-3`, diagram panel `col-span-9`
- **Pin height:** `min-h-[min(62vh,600px)]`
- **ScrollTrigger pin** with scrub `0.35`, snap to step indices
- **Panel layout:** diagram `xl:col-span-7`, copy + chips `xl:col-span-5`

### Mobile workflow
- Stacked cards per step; diagram above copy; `Reveal`-style scroll fade-in

### Capabilities
- `grid md:grid-cols-2`, gap `5` / `xl:gap-7`
- Visual aspect: **`16/10`**

### Intelligence stack
- Mobile: vertical column + downward arrows
- Desktop: horizontal row + rightward arrows (`lg:flex-row`)
- Max width: `max-w-6xl`

### Before / After
- `max-w-5xl`, `md:grid-cols-2`
- Center arrow badge on desktop: `h-12 w-12`, `border-outline-variant/60`

### Deployment
- `md:grid-cols-4`, scrubbed progress bar on desktop

---

## 6. Component vocabulary

### 6.1 SectionHeading
- Eyebrow: `text-primary`, `mb-3`
- Title: light → `text-on-surface`; dark → `text-on-secondary`
- Description: light → `text-on-surface-variant`; dark → `text-on-secondary/80`

### 6.2 Chips / bullets (journey)
```html
rounded-full border border-primary/25 bg-primary/8 px-3 py-1.5 text-xs font-medium
```

### 6.3 DiagramShell (workflow loop diagrams)
Shared wrapper for all five step visuals:

| Part | Spec |
|------|------|
| Outer | `aspect-[4/3] min-h-[300px] md:min-h-[360px] rounded-xl border-outline-variant/50 bg-surface-lowest p-5 md:p-6` |
| Eyebrow | `data-animate="label"`, primary uppercase |
| Stage | `rounded-lg border-outline-variant/40 bg-surface-low/60 p-4 md:p-5` |
| **DiagramCard** | `rounded-lg border-outline-variant/50 bg-surface-lowest shadow-sm` |
| **DiagramCallout** | `border-primary/25 bg-primary/8`, footer strip |
| **DiagramBadge** | `rounded-full border-primary/25 bg-primary/10 text-primary` |

### 6.4 Connect diagram (reference layout)
- Sources: 4 stacked cards, left column
- Lines: runtime-measured SVG dashes from card center-right → hub circle center-left
- Hub: circle with `bg-primary/8` glow + overlapping **Stamped** card on the right
- Stroke: `var(--brand-primary)`, opacity ~0.42, dash `6 4`, `strokeLinecap round`

### 6.5 Execute diagram (WhatsApp alert)
Structured notification card:
- Header row: label + timestamp (`Shift B · 06:42`)
- Bold prescription title
- **Why / Impact / Owner / Due** with semibold labels
- CTA strip: `border-primary/20 bg-primary/8 font-semibold text-primary`

### 6.6 Capability visuals (white inset panels)
All four use **`bg-surface-lowest`** canvas, ~**5s** animation duration, ScrollTrigger once:

| ID | Visual | Trigger start |
|----|--------|---------------|
| `ingestion` | 6-source orbit → Stamped hub | `top 88%` |
| `repository` | Energy graph hub → nodes → edges | `top 88%` |
| `intelligence` | Chart, baseline band, anomaly, prescription card | `top 76%` |
| `governance` | Square loop (Assign → Verify) → arrow down → Verified savings | `top 76%` |

Shared stroke language: `var(--brand-primary)`, dashed connectors, rounded node cards `text-[9px]–text-[11px]`.

### 6.7 Dashboard embed placeholder
- Aspect `16/10`, dashed `border-primary/35`
- Gradient fill: primary 6% → `surface-container-high`
- Grid overlay: primary 10%, 28px cells

---

## 7. Motion & interaction

### Stack
- **GSAP** + **ScrollTrigger** + **Lenis** smooth scroll (site-wide via `MotionProvider`)
- **`prefers-reduced-motion`:** animations skipped; static final states

### Global easing
- Enter: `power2.out`
- Draw / scrub: `power2.inOut`
- Pop: `back.out(1.4–1.6)`

### Section animation contracts

| Section | Trigger | Behavior |
|---------|---------|----------|
| Opening | On mount | Stagger fade-up `y:28`, 0.85s |
| Plant SLD | `top 82%` once | Lines draw → nodes pop |
| Pinned journey | Pin + scrub | Step nav highlight; `animateDiagramPanel` per step |
| Intelligence stack | `top 78%` / `82%` | Sequential cards + arrow draw; glow at end |
| Prescription | `Reveal` | Standard fade-in |
| Capabilities | `top 78%` | Cards stagger `y:28` |
| Before/After | `top 72%` | Cards slide ±24px; items stagger |
| Deployment | `top 78%` + scrub bar | Phases fade; progress `scaleX` |
| Final CTA | `top 80%` | Fade-up `y:32` |

### Workflow diagram animation (`animateDiagram.ts`)
Unified sequence per step:
1. **Label** — fade down, 0.38s  
2. **Items** — stagger 0.09, slide ±14px, 0.44s  
3. **Accent** — scale pop, delay 0.42s  
4. **Footer** — fade up, delay 0.62s (where present)  
5. **Connect** — measured SVG line draw, stagger 0.08  

### Pin scroll (desktop journey)
- `scrub: 0.35`
- `snap: 1/(steps-1)`, duration 0.15–0.35s
- Active step: `border-primary/50 bg-primary/5 shadow-md`, scale 1.02

---

## 8. Content architecture

All strings live in **`lib/content/howItWorks.ts`**. Key blocks:

```
hero, plantSld, journey, intelligenceStack, prescriptionDemo,
capabilities, beforeAfter, deployment, gifSlots, finalCta
```

### Journey steps (diagram keys)
| Step | ID | Diagram component |
|------|-----|-------------------|
| 1 Connect | `connect` | `ConnectDiagram` |
| 2 Observe | `observe` | `ObserveDiagram` |
| 3 Decide | `decide` | `DecideDiagram` |
| 4 Execute | `execute` | `ExecuteDiagram` |
| 5 Verify | `verify` | `VerifyDiagram` |

### Capabilities (media-ready)
Each capability has `mediaSrc: null` — swap for GIF/WebM without layout changes.

### Placeholder slots
- Prescription embed: iframe/video/placeholder via `DashboardEmbed`
- `gifSlots` — optional future captures

---

## 9. Border radius & elevation

| Element | Radius |
|---------|--------|
| Buttons | `md` (8px) — site `Button` |
| Diagram cards / nodes | `rounded-lg` (8px) |
| Section cards | `rounded-xl` (12px) |
| Capability cards | `rounded-2xl` (16px) |
| Plant SLD | `rounded-2xl` |
| Hub circles | `rounded-full` |
| Chips | `rounded-full` |

**Elevation philosophy:** borders + subtle shadows, not heavy drop shadows. Primary coral defines “active” elevation.

---

## 10. Accessibility

- Plant SLD nodes: focusable buttons, `aria-label` with tooltip text, `aria-live` hint bar
- Diagram SVGs: `aria-hidden="true"` where decorative
- Reduced motion respected globally
- Color contrast: on-surface on surface-lowest meets AA for body; primary on white for large text / UI chrome

---

## 11. File map (implementation)

```
app/how-it-works/page.tsx          — section order & metadata
lib/content/howItWorks.ts          — all copy & structured content
lib/motion/animateDiagram.ts       — workflow diagram animations
lib/motion/pinLayout.ts            — pin start offset

components/how-it-works/
  HiwOpening.tsx                   — hero + SLD
  PlantSldDiagram.tsx              — interactive opening diagram
  HiwPinnedJourney.tsx             — pinned 5-step journey
  diagrams/                        — DiagramShell + 5 step diagrams
  HiwIntelligenceStack.tsx         — 4-layer stack
  HiwPrescriptionWalkthrough.tsx   — dashboard embed
  DashboardEmbed.tsx
  HiwCapabilities.tsx              — 4 capability cards
  capabilities/                    — GSAP visuals (ingestion, repo, intel, gov)
  HiwBeforeAfter.tsx
  HiwDeployment.tsx
  HiwPageCta.tsx
```

---

## 12. Do / Don’t (page-specific)

### Do
- Keep diagram canvases **white** inside dark capability cards
- Use **primary coral** for data flow lines and active workflow steps
- Maintain **diagram-first** density — chips over bullet walls
- Alternate light/dark sections for scroll rhythm
- Measure connector lines dynamically (Connect diagram) when DOM layout is used

### Don’t
- Introduce off-brand colors (e.g. WhatsApp green) — use primary-tinted surfaces
- Mix diagram styles across the five workflow steps — use `DiagramShell` primitives
- Add long prose blocks to journey steps — tagline + chips only
- Place capabilities above the workflow loop (current order is intentional: journey → stack → product → capabilities)

---

## 13. Related documents

| File | Relationship |
|------|--------------|
| `Deisgn_Stamped_Energy_original.md` | Global brand tokens & philosophy |
| `styles/theme.css` | Single source of truth for hex values |
| `DECISIONS.md` | ADR: Option C opening (SLD + capabilities) |
| `IMPLEMENTATION_PLAN.md` | Phase history for HIW build |
| `lib/content/howItWorks.ts` | Live content — sync copy changes here first |

---

*This dock describes the page as implemented. When visuals or tokens change, update this file in the same PR.*
