# Founder OS — Self-Evolving Agent: Build Plan

This document is the **reference blueprint** for upgrading Founder OS from an
intent-routing assistant into a **true agentic, self-evolving system**. Build
against this file. Keep it updated as the source of truth.

---

## 1. Vision

A single-user (the founder) personal AI that:

1. **Acts agentically** — given any goal, it decides *which* tools to call, in
   *what order*, looping until the goal is met (not a fixed intent → branch).
2. **Self-evolves** — it learns from every interaction: records lessons, writes
   reusable "skills" (playbooks), and rewrites its own operating instructions.
   Its system prompt is assembled dynamically from this growing knowledge.
3. **Is proactive / autonomous** — a scheduled heartbeat lets it review goals,
   reminders, and the CRM pipeline, then act or propose actions on its own.
4. **Is safe** — irreversible/external actions (sending email, posting to X,
   deleting calendar events, modifying its own code) pass through a human
   **approval gate** unless auto-approve is explicitly enabled.

### What "self-evolving" means here (and its limits)
- **In scope (safe):** learns lessons, creates/updates skills, rewrites its own
  *instructions* (a markdown operating manual injected into every prompt),
  tunes which tools/strategies it prefers, reflects on outcomes.
- **Out of scope by default (gated):** rewriting its own *Python source code*.
  A `propose_code_change` tool can draft a change, but it only ever produces a
  proposal for human review + approval. No unsupervised self-modification of
  executable code. This is a deliberate safety boundary.

---

## 2. Capability feasibility (the original questions)

| Capability | Status | How |
|---|---|---|
| Reminders | ✅ built | `set_reminder` tool → APScheduler one-off/recurring job → Telegram ping |
| Google Calendar | ✅ built (needs OAuth) | `integrations/google_calendar.py`, official API, `scripts/google_auth.py` |
| Autonomous multi-step action | ✅ built | tool-calling loop + heartbeat + goals |
| X (Twitter) post | ⚠️ built, gated, needs paid API | `integrations/x_client.py` (tweepy), approval-gated |
| X browse/read | ⚠️ limited | API rate/paywall limited; best-effort |
| LinkedIn post | ❌ draft-only | API closed for personal posting; agent drafts, user posts |
| LinkedIn auto-browse | ❌ not built | violates LinkedIn ToS / account-ban risk |

---

## 3. Architecture

```
Telegram ─► bot/handlers.py ─► agent/core.py  (the agentic loop)
                                   │
                                   ├─ llm/tool_client.py   (tool-calling completions, provider fallback)
                                   ├─ agent/identity.py     (dynamic system prompt)
                                   ├─ agent/registry.py     (tool registry + schemas + exec)
                                   ├─ agent/tools/*         (all callable tools)
                                   ├─ agent/approvals.py     (risky-action queue)
                                   ├─ agent/evolution.py     (lessons / skills / reflection)
                                   └─ agent/store.py         (SQLite: reminders, goals, lessons, skills, approvals, action_log)
scheduler/jobs.py ─► reminder dispatch · heartbeat (proactivity) · nightly reflection
```

### The agentic loop (`agent/core.py`)
1. Build system prompt (identity + self-instructions + retrieved skills + lessons + current time).
2. Assemble messages: system + recent history + retrieved long-term memory + user turn.
3. Call `tool_client` with the full tool schema list.
4. If the model returns `tool_calls`: execute each (or enqueue if it needs approval), append results, loop.
5. If the model returns content: that's the final answer. Log the turn, fire async reflection if notable.
6. Hard cap on steps (e.g. 8) to prevent runaway loops.

### Provider strategy
- Tool calling runs on OpenAI-compatible providers: **Groq (llama-3.3-70b) → OpenAI (gpt-4o-mini)**.
- Gemini stays available for plain completions via the existing `llm/router.py`.

---

## 4. Data model (new tables, same `data/founder_os.db`)

- `reminders(id, text, due_at, repeat, status, created_at)`
- `goals(id, title, detail, status, priority, created_at, updated_at)`
- `lessons(id, situation, lesson, tags, created_at)` — what worked / what didn't
- `skills(id, name, when_to_use, steps, created_at, updated_at)` — reusable playbooks
- `approvals(id, kind, tool_name, args_json, summary, status, created_at, decided_at)`
- `action_log(id, actor, tool_name, args_json, result, created_at)` — full audit trail

Self-instructions live as a file: `data/agent_state/instructions.md` (editable by
the agent via the `update_instructions` tool).

---

## 5. Tools (the agent's hands)

**Memory / knowledge**
- `search_memory(query)` · `save_memory(text, tags)` · `recent_memory(limit)`
- `ingest(content)` — classify + file arbitrary content

**CRM / pipeline**
- `add_contact` · `update_contact_status` · `set_followup` · `search_contacts`
- `get_followups` · `pipeline_status`

**Research / web**
- `research_company(name)` · `web_search(query)` · `scrape_url(url)` · `find_leads(...)`

**Outreach** (send is approval-gated)
- `draft_email(...)` · `send_email(to, subject, body)` 🔒 · `draft_linkedin(...)`

**Tasks & reminders**
- `add_task` · `list_tasks` · `complete_task`
- `set_reminder(text, due_at_iso, repeat)` · `list_reminders` · `cancel_reminder`

**Calendar** (Google)
- `calendar_create_event(...)` · `calendar_list_events(...)` · `calendar_delete_event(id)` 🔒

**Social**
- `x_post(text)` 🔒 · `x_search(query)`
- `draft_linkedin_post(topic)` (draft only — no auto-post)

**Goals & autonomy**
- `add_goal` · `list_goals` · `update_goal`

**Self-evolution**
- `record_lesson(situation, lesson, tags)`
- `save_skill(name, when_to_use, steps)` · `find_skill(query)`
- `update_instructions(section, content, mode=append|replace)`
- `propose_code_change(file, rationale, diff)` 🔒 (human review only)

🔒 = approval-gated when `AUTO_APPROVE` is off (default).

---

## 6. Self-evolution mechanism

1. **Capture** — after each notable turn, an async reflection pass asks the model:
   *what did I learn, what would I do differently, is there a reusable skill here?*
   It then calls `record_lesson` / `save_skill` / `update_instructions` as needed.
2. **Store** — lessons & skills go to SQLite **and** the vector store for retrieval.
3. **Retrieve** — at the start of every loop, relevant skills + lessons are pulled
   by semantic search and injected into the system prompt.
4. **Rewrite** — `update_instructions` lets the agent edit its own operating manual,
   which is always injected. This is the core evolutionary feedback loop.
5. **Feedback** — explicit user corrections ("no, do it like X") are turned into
   high-priority lessons immediately.

---

## 7. Autonomy / proactivity (`scheduler/jobs.py`)

- **Reminder dispatch** — due reminders ping the user; recurring ones reschedule.
- **Heartbeat** (e.g. every few hours during the day) — the agent reviews goals,
  due follow-ups, and reminders, then sends a short proactive nudge/digest and
  *proposes* next actions. External actions still go through approval.
- **Nightly reflection** — consolidates the day's interactions into lessons and
  prunes/clarifies instructions.

---

## 8. Approval gate (`agent/approvals.py`)

- Risky tool called → instead of executing, create an `approvals` row + tell the
  user: *"Proposed: <summary>. Reply `approve <id>` or `reject <id>`."*
- `approve <id>` → execute the stored action via the registry, log it, report back.
- `reject <id>` → mark rejected, optionally record a lesson about why.
- `AUTO_APPROVE=true` (config) bypasses the gate for power users.

---

## 9. Config additions (`.env`)

```
# Autonomy
AUTO_APPROVE=false
HEARTBEAT_HOURS=4

# Google Calendar (optional) — run scripts/google_auth.py once
GOOGLE_CREDENTIALS_PATH=./data/google_credentials.json
GOOGLE_TOKEN_PATH=./data/google_token.json

# X / Twitter (optional, paid API)
X_API_KEY=
X_API_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_TOKEN_SECRET=
X_BEARER_TOKEN=
```

New Python deps (optional ones imported lazily so missing libs never crash boot):
`google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `tweepy`.

---

## 10. Safety principles

1. Default-deny on irreversible/external actions (approval gate).
2. Never self-modify executable code unsupervised.
3. Full audit trail in `action_log`.
4. Step cap on the loop; timeouts on tools.
5. Single authorized Telegram user only.

---

## 11. Build order (tracked in the todo list)

1. `PLAN.md` (this file)
2. `agent/store.py` — new tables
3. `llm/tool_client.py` — tool-calling completions
4. `agent/registry.py` — registry + schemas + exec
5. `agent/identity.py` — dynamic prompt + self-instructions
6. `agent/tools/*` — all tools
7. `agent/approvals.py`
8. `agent/evolution.py`
9. `agent/core.py` — the loop
10. `scheduler/jobs.py` — reminders + heartbeat + reflection
11. `bot/handlers.py` — wire to core + approval commands
12. `config.py`, `requirements.txt`, `.env.example`
13. Smoke test (imports + dry run)
