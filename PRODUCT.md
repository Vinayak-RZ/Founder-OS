# Product

## Register
product

## Users & purpose
**Single operator (Vinayak)** — Founder OS is a personal platform for handling the many parallel threads of founder life: Stamped Energy, side projects, research ideas, outreach, CRM, goals, and linked documentation.

It is an **aggregator hub**, not a deep research or coding workstation. Extensive research, writing, and build work happen in **Cursor**, **Claude**, and Git repos; Founder OS **ingests**, **tracks**, and lets you **query** that work while coordinating outreach and status.

## Primary surface
**Web dashboard** at `http://127.0.0.1:8787` (default). Telegram is optional legacy.

**Deployment target:** AWS — EC2 for the app, S3 for vault artifacts and backups, Qdrant Cloud for vectors.

## Core capabilities
- **Worlds** — root world + sub-worlds per company/project/idea; active world scopes chat and vault
- **Knowledge vault** — per-world facet folders, link local GitHub doc clones, ingest, semantic search
- **Agent fleet** — Pulse, Outreach, Leads, Market intel, Vault (aggregator specialists, max ~5)
- **Outreach & CRM** — drafts, approval-gated sends, pipeline, inbox reply tracking
- **Integrations** — Gmail/Calendar via `.env` today; **Settings → Connect** for GitHub, Gmail, LinkedIn, X (roadmap)

## Brand personality
Capable, calm, direct. A serious personal operator console — not a toy chatbot, not enterprise bloat. Stamped Energy / Forge Industrial visual language (coral accent, black nav, warm greys, Plus Jakarta Sans).

## Anti-references
- Generic AI SaaS (purple gradients, glass cards)
- Chat-only UIs with no operational visibility
- All-in-one “do everything” research IDE — deep work stays external

## Strategic principles
1. **Aggregator over depth** — coordinate and query; don't replace Cursor for heavy work
2. **Web-first** — full visibility: chat, worlds, vault, approvals, CRM
3. **One user** — personal platform, not multi-tenant
4. **Trust through control** — approval gates, traces, honest vault citations
5. **Accessible by default** — WCAG AA, keyboard nav, reduced-motion

## Accessibility
WCAG 2.1 AA minimum. Respect `prefers-reduced-motion`. Focus rings on all interactive elements.
