# Cursor Agent Prompt — Founder OS (Full Build)

> **HOW TO USE THIS:** Open Cursor. Switch to **Agent mode** (top of composer). Paste this entire file as your first message. The agent will ask you for credentials first, then build everything end to end. Make commits at every checkpoint marked `🔵 COMMIT`.

---

## AGENT INSTRUCTIONS

You are building a complete, production-ready, locally-running **Founder Operating System** that the user interacts with through Telegram. This is a full agentic build — you will plan, scaffold, implement, test, and guide commits for every single piece of this system from scratch. Do not summarize. Do not skip steps. Do not say "you can implement this later." Build everything now.

---

## STEP 0 — COLLECT CREDENTIALS BEFORE WRITING ANY CODE

Before writing a single line of code, output this exact numbered list and tell the user to reply with all values:

```
I need the following before I can start building. Reply with all of them:

1. TELEGRAM_BOT_TOKEN
   → Go to Telegram, message @BotFather
   → Send /newbot, follow the prompts, copy the token it gives you

2. GROQ_API_KEY
   → Go to https://console.groq.com
   → Sign up free, go to API Keys, create one

3. GOOGLE_GEMINI_API_KEY
   → Go to https://aistudio.google.com/app/apikey
   → Sign in, click "Create API Key", copy it

4. OPENAI_API_KEY
   → You already have this — paste it here

5. GMAIL_ADDRESS
   → The Gmail you want to send outreach emails FROM

6. GMAIL_APP_PASSWORD
   → Go to myaccount.google.com
   → Security → 2-Step Verification (enable if not on) → App Passwords
   → Generate one for "Mail" / "Other", copy the 16-char password

7. MY_TELEGRAM_USER_ID (a number, not your username)
   → Message @userinfobot on Telegram
   → It will reply with your numeric ID — paste it here

8. SERPER_API_KEY
   → Go to https://serper.dev
   → Sign up free (2500 searches/month free), copy your API key

9. MY_NAME — Your full name

10. MY_COMPANY_NAME — Your startup name

11. MY_ROLE — Your title (e.g. Co-founder & CEO)

12. MY_ONE_LINER — One sentence describing what your company does
```

**Wait for the user to reply with all 12 values before proceeding.**

Once received, confirm: "Got everything. Starting the build now." Then proceed to Step 1.

---

## STEP 1 — PROJECT SCAFFOLD

Create the following directory and file structure. Create every file, even if initially empty:

```
founder-os/
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── main.py
├── config.py
├── bot/
│   ├── __init__.py
│   ├── handlers.py
│   ├── middleware.py
│   └── formatters.py
├── orchestrator/
│   ├── __init__.py
│   ├── router.py
│   ├── context.py
│   └── response_builder.py
├── agents/
│   ├── __init__.py
│   ├── research_agent.py
│   ├── outreach_agent.py
│   ├── memory_agent.py
│   ├── crm_agent.py
│   └── report_agent.py
├── llm/
│   ├── __init__.py
│   ├── router.py
│   ├── groq_client.py
│   ├── gemini_client.py
│   └── openai_client.py
├── memory/
│   ├── __init__.py
│   ├── vector_store.py
│   └── sql_store.py
├── outreach/
│   ├── __init__.py
│   ├── email_sender.py
│   └── tracker.py
├── scheduler/
│   ├── __init__.py
│   └── jobs.py
├── tools/
│   ├── __init__.py
│   ├── web_search.py
│   ├── scraper.py
│   └── utils.py
└── data/
    └── .gitkeep
```

### .gitignore
```
.env
data/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/
.venv/
venv/
*.log
.DS_Store
```

### .env
Populate with all 12 values the user provided:
```
TELEGRAM_BOT_TOKEN=
GROQ_API_KEY=
GOOGLE_GEMINI_API_KEY=
OPENAI_API_KEY=
GMAIL_ADDRESS=
GMAIL_APP_PASSWORD=
MY_TELEGRAM_USER_ID=
SERPER_API_KEY=
MY_NAME=
MY_COMPANY_NAME=
MY_ROLE=
MY_ONE_LINER=
```

### .env.example
Same as above but all values empty (safe to commit).

### requirements.txt
```
python-telegram-bot==20.7
groq==0.4.2
google-generativeai==0.4.1
openai==1.12.0
chromadb==0.4.22
python-dotenv==1.0.1
aiohttp==3.9.3
requests==2.31.0
beautifulsoup4==4.12.3
APScheduler==3.10.4
aiosqlite==0.20.0
lxml==5.1.0
```

---

## 🔵 COMMIT 1
After creating all files and directories:
```
git init
git add .
git commit -m "feat: initial project scaffold"
```
Tell the user: "Commit 1 done — scaffold created. Now building the core modules."

---

## STEP 2 — CONFIG MODULE

### config.py
```python
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    telegram_bot_token: str
    groq_api_key: str
    gemini_api_key: str
    openai_api_key: str
    gmail_address: str
    gmail_app_password: str
    my_telegram_user_id: int
    serper_api_key: str
    my_name: str
    company_name: str
    my_role: str
    my_one_liner: str

def load_config() -> Config:
    required = {
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        "MY_TELEGRAM_USER_ID": os.getenv("MY_TELEGRAM_USER_ID"),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        print(f"[FATAL] Missing required env vars: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in all values.")
        exit(1)

    return Config(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        gemini_api_key=os.getenv("GOOGLE_GEMINI_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        gmail_address=os.getenv("GMAIL_ADDRESS", ""),
        gmail_app_password=os.getenv("GMAIL_APP_PASSWORD", ""),
        my_telegram_user_id=int(os.getenv("MY_TELEGRAM_USER_ID", "0")),
        serper_api_key=os.getenv("SERPER_API_KEY", ""),
        my_name=os.getenv("MY_NAME", "Founder"),
        company_name=os.getenv("MY_COMPANY_NAME", "My Company"),
        my_role=os.getenv("MY_ROLE", "Founder"),
        my_one_liner=os.getenv("MY_ONE_LINER", ""),
    )

config = load_config()
```

---

## STEP 3 — LLM LAYER

### llm/groq_client.py
```python
from groq import AsyncGroq
from config import config

client = AsyncGroq(api_key=config.groq_api_key)

class RateLimitError(Exception):
    pass

async def complete(messages: list, max_tokens: int = 2048) -> str:
    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        if "rate_limit" in str(e).lower() or "429" in str(e):
            raise RateLimitError(str(e))
        raise
```

### llm/gemini_client.py
```python
import google.generativeai as genai
from config import config

genai.configure(api_key=config.gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

async def complete(messages: list, max_tokens: int = 2048) -> str:
    # Convert OpenAI-style messages to Gemini format
    prompt_parts = []
    for m in messages:
        role = m["role"]
        content = m["content"]
        if role == "system":
            prompt_parts.append(f"[System Instructions]\n{content}\n")
        elif role == "user":
            prompt_parts.append(f"User: {content}")
        elif role == "assistant":
            prompt_parts.append(f"Assistant: {content}")
    prompt = "\n".join(prompt_parts)

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens),
        )
        return response.text
    except Exception as e:
        raise
```

### llm/openai_client.py
```python
from openai import AsyncOpenAI
from config import config

client = AsyncOpenAI(api_key=config.openai_api_key)

async def complete(messages: list, max_tokens: int = 2048) -> str:
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content
```

### llm/router.py
```python
import logging
from llm import groq_client, gemini_client, openai_client
from llm.groq_client import RateLimitError

logger = logging.getLogger(__name__)

# Task type → preferred model chain
ROUTING = {
    "general":   ["groq", "gemini", "openai"],
    "research":  ["gemini", "groq", "openai"],
    "outreach":  ["groq", "gemini", "openai"],
    "analysis":  ["gemini", "groq", "openai"],
}

CLIENTS = {
    "groq":   groq_client.complete,
    "gemini": gemini_client.complete,
    "openai": openai_client.complete,
}

async def complete(messages: list, task_type: str = "general", max_tokens: int = 2048) -> str:
    chain = ROUTING.get(task_type, ROUTING["general"])
    last_error = None

    for model_name in chain:
        try:
            logger.info(f"LLM call: model={model_name}, task={task_type}")
            result = await CLIENTS[model_name](messages, max_tokens=max_tokens)
            logger.info(f"LLM success: model={model_name}")
            return result
        except RateLimitError as e:
            logger.warning(f"Rate limit on {model_name}, trying next. Error: {e}")
            last_error = e
            continue
        except Exception as e:
            logger.error(f"Error on {model_name}: {e}, trying next.")
            last_error = e
            continue

    raise Exception(f"All LLM providers failed. Last error: {last_error}")
```

---

## STEP 4 — MEMORY LAYER

### memory/vector_store.py
```python
import chromadb
from chromadb.config import Settings
import os
import time
import uuid

os.makedirs("./data/chroma", exist_ok=True)

client = chromadb.PersistentClient(path="./data/chroma")

COLLECTIONS = ["conversations", "research", "notes", "outreach"]

def get_collection(name: str):
    return client.get_or_create_collection(name)

def add(collection_name: str, text: str, metadata: dict = None, doc_id: str = None):
    col = get_collection(collection_name)
    doc_id = doc_id or str(uuid.uuid4())
    meta = {"timestamp": time.time(), "source": collection_name}
    if metadata:
        meta.update(metadata)
    col.add(documents=[text], metadatas=[meta], ids=[doc_id])
    return doc_id

def search(collection_name: str, query: str, n_results: int = 5) -> list:
    col = get_collection(collection_name)
    count = col.count()
    if count == 0:
        return []
    results = col.query(query_texts=[query], n_results=min(n_results, count))
    items = []
    for i, doc in enumerate(results["documents"][0]):
        items.append({
            "text": doc,
            "metadata": results["metadatas"][0][i],
            "id": results["ids"][0][i],
            "distance": results["distances"][0][i] if results.get("distances") else None,
            "collection": collection_name,
        })
    return items

def search_all(query: str, n_results: int = 3) -> list:
    all_results = []
    for col_name in COLLECTIONS:
        results = search(col_name, query, n_results=n_results)
        all_results.extend(results)
    # Sort by distance (lower = more relevant)
    all_results.sort(key=lambda x: x.get("distance") or 999)
    return all_results[:n_results * 2]

def delete(collection_name: str, doc_id: str):
    col = get_collection(collection_name)
    col.delete(ids=[doc_id])

def get_recent(collection_name: str, limit: int = 10) -> list:
    col = get_collection(collection_name)
    count = col.count()
    if count == 0:
        return []
    results = col.get(limit=min(limit, count), include=["documents", "metadatas"])
    items = []
    for i, doc in enumerate(results["documents"]):
        items.append({
            "text": doc,
            "metadata": results["metadatas"][i],
            "id": results["ids"][i],
        })
    # Sort by timestamp descending
    items.sort(key=lambda x: x["metadata"].get("timestamp", 0), reverse=True)
    return items
```

### memory/sql_store.py
```python
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional

os.makedirs("./data", exist_ok=True)
DB_PATH = "./data/founder_os.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        company TEXT,
        role TEXT,
        email TEXT,
        linkedin_url TEXT,
        phone TEXT,
        source TEXT,
        status TEXT DEFAULT 'prospect',
        priority INTEGER DEFAULT 3,
        notes TEXT,
        last_contacted_at TIMESTAMP,
        next_followup_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS outreach_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_id INTEGER REFERENCES contacts(id),
        channel TEXT,
        direction TEXT,
        subject TEXT,
        body TEXT,
        status TEXT DEFAULT 'sent',
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        website TEXT,
        industry TEXT,
        size TEXT,
        location TEXT,
        description TEXT,
        research_summary TEXT,
        icp_score INTEGER,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'pending',
        priority INTEGER DEFAULT 3,
        due_at TIMESTAMP,
        completed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        tags TEXT,
        linked_contact_id INTEGER REFERENCES contacts(id),
        linked_company_id INTEGER REFERENCES companies(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()

# ── CONTACTS ─────────────────────────────────────────────────────────────────

def add_contact(name, company=None, role=None, email=None, linkedin_url=None,
                phone=None, source=None, status="prospect", priority=3, notes=None) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO contacts (name, company, role, email, linkedin_url, phone, source, status, priority, notes)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (name, company, role, email, linkedin_url, phone, source, status, priority, notes))
    conn.commit()
    contact_id = c.lastrowid
    conn.close()
    return contact_id

def update_contact(contact_id: int, **kwargs):
    kwargs["updated_at"] = datetime.now().isoformat()
    conn = get_conn()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    conn.execute(f"UPDATE contacts SET {sets} WHERE id = ?", (*kwargs.values(), contact_id))
    conn.commit()
    conn.close()

def get_contact(contact_id: int) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def search_contacts(query: str) -> list:
    conn = get_conn()
    q = f"%{query}%"
    rows = conn.execute(
        "SELECT * FROM contacts WHERE name LIKE ? OR company LIKE ? OR role LIKE ? OR email LIKE ? ORDER BY updated_at DESC",
        (q, q, q, q)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_contacts_needing_followup() -> list:
    conn = get_conn()
    now = datetime.now().isoformat()
    rows = conn.execute(
        "SELECT * FROM contacts WHERE next_followup_at <= ? AND status NOT IN ('closed', 'dead') ORDER BY next_followup_at ASC",
        (now,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_pipeline_summary() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT status, COUNT(*) as count FROM contacts GROUP BY status").fetchall()
    conn.close()
    return {r["status"]: r["count"] for r in rows}

def get_all_contacts() -> list:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM contacts ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── OUTREACH LOG ──────────────────────────────────────────────────────────────

def log_outreach(contact_id: int, channel: str, direction: str,
                 subject: str = None, body: str = None, status: str = "sent") -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO outreach_log (contact_id, channel, direction, subject, body, status)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (contact_id, channel, direction, subject, body, status))
    conn.commit()
    log_id = c.lastrowid
    conn.close()
    return log_id

def get_recent_outreach(days: int = 7) -> list:
    conn = get_conn()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """SELECT ol.*, c.name as contact_name, c.company
           FROM outreach_log ol
           LEFT JOIN contacts c ON ol.contact_id = c.id
           WHERE ol.sent_at >= ?
           ORDER BY ol.sent_at DESC""",
        (cutoff,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── COMPANIES ─────────────────────────────────────────────────────────────────

def add_company(name, website=None, industry=None, size=None, location=None,
                description=None, research_summary=None, icp_score=None, notes=None) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO companies (name, website, industry, size, location, description, research_summary, icp_score, notes)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (name, website, industry, size, location, description, research_summary, icp_score, notes))
    conn.commit()
    company_id = c.lastrowid
    conn.close()
    return company_id

def search_companies(query: str) -> list:
    conn = get_conn()
    q = f"%{query}%"
    rows = conn.execute(
        "SELECT * FROM companies WHERE name LIKE ? OR industry LIKE ? ORDER BY updated_at DESC",
        (q, q)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── TASKS ─────────────────────────────────────────────────────────────────────

def add_task(title: str, description: str = None, priority: int = 3, due_at: str = None) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO tasks (title, description, priority, due_at) VALUES (?, ?, ?, ?)",
              (title, description, priority, due_at))
    conn.commit()
    task_id = c.lastrowid
    conn.close()
    return task_id

def get_pending_tasks() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE status = 'pending' ORDER BY priority ASC, due_at ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def complete_task(task_id: int):
    conn = get_conn()
    conn.execute("UPDATE tasks SET status = 'done', completed_at = ? WHERE id = ?",
                 (datetime.now().isoformat(), task_id))
    conn.commit()
    conn.close()

# ── NOTES ─────────────────────────────────────────────────────────────────────

def add_note(content: str, tags: str = None, contact_id: int = None, company_id: int = None) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO notes (content, tags, linked_contact_id, linked_company_id) VALUES (?, ?, ?, ?)",
              (content, tags, contact_id, company_id))
    conn.commit()
    note_id = c.lastrowid
    conn.close()
    return note_id

def get_recent_notes(limit: int = 20) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM notes ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Run on import
init_db()
```

---

## 🔵 COMMIT 2
```
git add .
git commit -m "feat: config, LLM router, memory layer (vector + SQL)"
```
Tell the user: "Commit 2 done — LLM and memory modules complete."

---

## STEP 5 — TOOLS

### tools/web_search.py
```python
import requests
from config import config

def search(query: str, num_results: int = 5) -> list:
    """Search the web using Serper.dev and return structured results."""
    if not config.serper_api_key:
        return _duckduckgo_fallback(query, num_results)

    headers = {"X-API-KEY": config.serper_api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": num_results}

    try:
        response = requests.post("https://google.serper.dev/search", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []
        for r in data.get("organic", [])[:num_results]:
            results.append({
                "title": r.get("title"),
                "url": r.get("link"),
                "snippet": r.get("snippet"),
            })
        return results
    except Exception as e:
        print(f"[Search] Serper error: {e}, falling back to DuckDuckGo")
        return _duckduckgo_fallback(query, num_results)

def _duckduckgo_fallback(query: str, num_results: int = 5) -> list:
    """Free fallback using DuckDuckGo instant answer API."""
    try:
        params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        r = requests.get("https://api.duckduckgo.com/", params=params, timeout=10)
        data = r.json()
        results = []
        if data.get("AbstractText"):
            results.append({"title": data.get("Heading", query), "url": data.get("AbstractURL", ""), "snippet": data.get("AbstractText", "")})
        for topic in data.get("RelatedTopics", [])[:num_results - 1]:
            if "Text" in topic:
                results.append({"title": topic.get("Text", "")[:60], "url": topic.get("FirstURL", ""), "snippet": topic.get("Text", "")})
        return results[:num_results]
    except Exception:
        return []
```

### tools/scraper.py
```python
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FounderOS/1.0)"}

def scrape_url(url: str, max_chars: int = 3000) -> dict:
    """Scrape a URL and return title + cleaned text."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "lxml")

        # Remove clutter
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title else ""
        text = " ".join(soup.get_text(separator=" ").split())[:max_chars]

        return {"url": url, "title": title, "text": text, "error": None}
    except Exception as e:
        return {"url": url, "title": "", "text": "", "error": str(e)}

def scrape_multiple(urls: list, max_chars_each: int = 2000) -> list:
    return [scrape_url(url, max_chars_each) for url in urls[:5]]
```

### tools/utils.py
```python
from datetime import datetime

def format_contact(contact: dict) -> str:
    """Format a contact dict for display in Telegram."""
    lines = [f"*{contact.get('name', 'Unknown')}*"]
    if contact.get("role"):
        lines.append(f"  Role: {contact['role']}")
    if contact.get("company"):
        lines.append(f"  Company: {contact['company']}")
    if contact.get("email"):
        lines.append(f"  Email: {contact['email']}")
    if contact.get("linkedin_url"):
        lines.append(f"  LinkedIn: {contact['linkedin_url']}")
    if contact.get("status"):
        lines.append(f"  Status: {contact['status']}")
    if contact.get("next_followup_at"):
        lines.append(f"  Follow-up: {contact['next_followup_at'][:10]}")
    return "\n".join(lines)

def now_iso() -> str:
    return datetime.now().isoformat()

def truncate(text: str, max_len: int = 3800) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "...\n_(truncated)_"
```

---

## STEP 6 — AGENTS

### agents/research_agent.py
```python
import json
from tools.web_search import search
from tools.scraper import scrape_url
from memory.vector_store import add as mem_add
from memory.sql_store import add_company, search_companies
from llm.router import complete

async def research_company(company_name: str) -> dict:
    """Full research pipeline for a company."""
    print(f"[Research] Starting research for: {company_name}")

    # Check if already researched
    existing = search_companies(company_name)
    if existing:
        return {"status": "cached", "company": existing[0], "summary": existing[0].get("research_summary", "")}

    # Step 1: Web searches
    overview_results = search(f"{company_name} company overview site:linkedin.com OR crunchbase.com OR {company_name}.com", num_results=5)
    leadership_results = search(f"{company_name} CEO founder leadership team", num_results=3)
    news_results = search(f"{company_name} news 2024 2025", num_results=3)

    # Step 2: Scrape top result
    scraped = {}
    if overview_results:
        scraped = scrape_url(overview_results[0]["url"])

    # Step 3: Build raw context
    raw = f"""
Company: {company_name}

SEARCH RESULTS (Overview):
{json.dumps(overview_results, indent=2)}

SEARCH RESULTS (Leadership):
{json.dumps(leadership_results, indent=2)}

SEARCH RESULTS (Recent News):
{json.dumps(news_results, indent=2)}

SCRAPED WEBSITE:
Title: {scraped.get('title', '')}
Content: {scraped.get('text', '')[:2000]}
"""

    # Step 4: LLM summary
    messages = [
        {"role": "system", "content": "You are a business research assistant. Extract and structure company information concisely."},
        {"role": "user", "content": f"""Based on this raw research data, produce a structured summary for: {company_name}

{raw}

Respond in this exact JSON format:
{{
  "name": "",
  "website": "",
  "industry": "",
  "size": "",
  "location": "",
  "what_they_do": "",
  "key_people": [
    {{"name": "", "role": "", "linkedin": ""}}
  ],
  "recent_news": "",
  "icp_score": 5,
  "icp_reasoning": "",
  "outreach_angle": ""
}}
Only output JSON, nothing else."""}
    ]

    raw_response = await complete(messages, task_type="research")

    try:
        # Strip any markdown fences
        clean = raw_response.strip().replace("```json", "").replace("```", "").strip()
        summary = json.loads(clean)
    except Exception:
        summary = {"name": company_name, "what_they_do": raw_response[:500], "error": "parse_failed"}

    # Save to SQL
    company_id = add_company(
        name=company_name,
        website=summary.get("website"),
        industry=summary.get("industry"),
        size=summary.get("size"),
        location=summary.get("location"),
        description=summary.get("what_they_do"),
        research_summary=json.dumps(summary),
        icp_score=summary.get("icp_score"),
    )

    # Save to vector memory
    mem_add("research", json.dumps(summary), metadata={"company": company_name, "type": "company_research"})

    return {"status": "new", "company_id": company_id, "summary": summary}
```

### agents/outreach_agent.py
```python
from llm.router import complete
from memory.sql_store import get_contact, search_contacts, search_companies
from memory.vector_store import search as mem_search
from config import config
import json

async def draft_email(contact_name: str = None, contact_id: int = None,
                      company_name: str = None, custom_context: str = "") -> dict:
    """Generate a personalized outreach email."""

    contact = None
    company_summary = ""

    if contact_id:
        contact = get_contact(contact_id)
    elif contact_name:
        results = search_contacts(contact_name)
        if results:
            contact = results[0]

    if company_name or (contact and contact.get("company")):
        cn = company_name or contact.get("company")
        companies = search_companies(cn)
        if companies and companies[0].get("research_summary"):
            try:
                cs = json.loads(companies[0]["research_summary"])
                company_summary = json.dumps(cs, indent=2)
            except Exception:
                company_summary = companies[0].get("research_summary", "")

    # Build personalization context
    contact_info = ""
    if contact:
        contact_info = f"""
Contact Name: {contact.get('name')}
Role: {contact.get('role', 'Unknown')}
Company: {contact.get('company', 'Unknown')}
LinkedIn: {contact.get('linkedin_url', '')}
Previous Notes: {contact.get('notes', '')}
"""

    messages = [
        {"role": "system", "content": f"""You are a cold outreach expert helping {config.my_name}, {config.my_role} at {config.company_name}.
{config.company_name}: {config.my_one_liner}

Write short, human, personalized cold emails. No fluff. No generic openers.
Max 5 sentences. End with a single, low-friction CTA."""},
        {"role": "user", "content": f"""Draft a cold outreach email.

SENDER:
Name: {config.my_name}
Role: {config.my_role}
Company: {config.company_name}
What we do: {config.my_one_liner}

RECIPIENT:
{contact_info if contact_info else f"Name: {contact_name or 'Unknown'}, Company: {company_name or 'Unknown'}"}

COMPANY RESEARCH:
{company_summary[:1500] if company_summary else "No research available yet. Use general personalization."}

ADDITIONAL CONTEXT:
{custom_context}

Respond in this exact JSON format:
{{
  "subject": "",
  "body": "",
  "linkedin_variant": "",
  "personalization_notes": ""
}}
Only output JSON."""}
    ]

    raw = await complete(messages, task_type="outreach")
    clean = raw.strip().replace("```json", "").replace("```", "").strip()

    try:
        draft = json.loads(clean)
    except Exception:
        draft = {"subject": "Following up", "body": raw[:1000], "linkedin_variant": "", "personalization_notes": ""}

    return draft

async def draft_linkedin_message(contact_name: str, company_name: str = "", context: str = "") -> str:
    """Draft a short LinkedIn connection request note (300 char limit)."""
    messages = [
        {"role": "system", "content": f"You write LinkedIn connection request notes for {config.my_name} at {config.company_name}. Max 280 characters. Human, specific, no buzzwords."},
        {"role": "user", "content": f"Write a LinkedIn note to {contact_name} at {company_name}. Context: {context or config.my_one_liner}. Only output the note text, nothing else."}
    ]
    result = await complete(messages, task_type="outreach", max_tokens=100)
    return result.strip()[:300]
```

### agents/memory_agent.py
```python
from memory.vector_store import add as vec_add, search_all
from memory.sql_store import add_note, get_recent_notes
from datetime import datetime

async def save(text: str, source: str = "user", tags: str = "") -> str:
    """Save anything to both vector memory and notes table."""
    doc_id = vec_add("notes", text, metadata={"source": source, "tags": tags, "timestamp": datetime.now().isoformat()})
    note_id = add_note(content=text, tags=tags)
    return f"Saved to memory (vector id: {doc_id}, note id: {note_id})"

async def recall(query: str) -> list:
    """Semantic search across all memory."""
    return search_all(query, n_results=5)

async def get_recent(limit: int = 10) -> list:
    return get_recent_notes(limit=limit)
```

### agents/crm_agent.py
```python
from memory.sql_store import (
    add_contact, update_contact, get_contact, search_contacts,
    get_contacts_needing_followup, get_pipeline_summary,
    log_outreach, add_task, get_pending_tasks
)
from tools.utils import format_contact
from datetime import datetime, timedelta

async def add(name: str, company: str = None, role: str = None, email: str = None,
              linkedin_url: str = None, source: str = "manual") -> dict:
    contact_id = add_contact(name=name, company=company, role=role,
                             email=email, linkedin_url=linkedin_url, source=source)
    return {"contact_id": contact_id, "message": f"Added {name} to CRM"}

async def update_status(contact_identifier: str, new_status: str) -> dict:
    contacts = search_contacts(contact_identifier)
    if not contacts:
        return {"error": f"No contact found matching '{contact_identifier}'"}
    contact = contacts[0]
    update_contact(contact["id"], status=new_status, updated_at=datetime.now().isoformat())
    return {"message": f"Updated {contact['name']} status to {new_status}"}

async def set_followup(contact_identifier: str, days: int = 3) -> dict:
    contacts = search_contacts(contact_identifier)
    if not contacts:
        return {"error": f"No contact found matching '{contact_identifier}'"}
    contact = contacts[0]
    followup_date = (datetime.now() + timedelta(days=days)).isoformat()
    update_contact(contact["id"], next_followup_at=followup_date)
    return {"message": f"Follow-up set for {contact['name']} in {days} days ({followup_date[:10]})"}

async def get_followups() -> list:
    contacts = get_contacts_needing_followup()
    return contacts

async def pipeline() -> str:
    summary = get_pipeline_summary()
    total = sum(summary.values())
    lines = [f"*Pipeline Summary* ({total} total contacts)", ""]
    status_emoji = {
        "prospect": "🔍", "contacted": "📤", "responded": "💬",
        "meeting_set": "📅", "closed": "✅", "dead": "❌"
    }
    for status, count in sorted(summary.items()):
        emoji = status_emoji.get(status, "•")
        lines.append(f"{emoji} {status.replace('_', ' ').title()}: {count}")
    return "\n".join(lines)

async def search(query: str) -> list:
    return search_contacts(query)

async def log_sent(contact_identifier: str, channel: str, subject: str = None, body: str = None):
    contacts = search_contacts(contact_identifier)
    if not contacts:
        return {"error": "Contact not found"}
    contact = contacts[0]
    log_id = log_outreach(contact["id"], channel=channel, direction="sent", subject=subject, body=body)
    update_contact(contact["id"], last_contacted_at=datetime.now().isoformat(), status="contacted")
    return {"log_id": log_id, "message": f"Logged {channel} outreach to {contact['name']}"}
```

### agents/report_agent.py
```python
from memory.sql_store import (
    get_contacts_needing_followup, get_pipeline_summary,
    get_recent_outreach, get_pending_tasks
)
from memory.vector_store import get_recent as vec_recent
from llm.router import complete
from datetime import datetime
import json

async def daily_briefing() -> str:
    """Generate a comprehensive daily briefing."""
    followups = get_contacts_needing_followup()
    pipeline = get_pipeline_summary()
    recent_outreach = get_recent_outreach(days=7)
    pending_tasks = get_pending_tasks()
    recent_memory = vec_recent("conversations", limit=5)

    data = {
        "date": datetime.now().strftime("%A, %B %d %Y"),
        "followups_due": len(followups),
        "followup_names": [f"{c['name']} @ {c.get('company', '?')}" for c in followups[:5]],
        "pipeline": pipeline,
        "outreach_last_7_days": len(recent_outreach),
        "pending_tasks": len(pending_tasks),
        "top_tasks": [t["title"] for t in pending_tasks[:3]],
    }

    messages = [
        {"role": "system", "content": "You are an executive assistant generating a crisp daily briefing for a startup founder. Use Telegram markdown formatting (* for bold). Be direct and action-oriented."},
        {"role": "user", "content": f"""Generate a daily briefing from this data:
{json.dumps(data, indent=2)}

Format:
- Opening with date and 1 sentence mood/priority
- Follow-ups section (who to contact today)
- Pipeline health (brief)
- Tasks section
- End with one power move recommendation for the day

Use Telegram markdown. Keep it under 400 words."""}
    ]

    return await complete(messages, task_type="analysis")
```

---

## 🔵 COMMIT 3
```
git add .
git commit -m "feat: tools, all agents (research, outreach, memory, CRM, report)"
```
Tell the user: "Commit 3 done — all agent modules built."

---

## STEP 7 — ORCHESTRATOR

### orchestrator/router.py
```python
import re
from llm.router import complete

INTENTS = [
    "research_company", "find_contacts", "draft_outreach", "send_email",
    "add_contact", "update_contact", "get_followups", "pipeline_status",
    "save_note", "search_memory", "add_task", "get_tasks", "daily_report", "general_chat"
]

async def classify_intent(message: str) -> dict:
    """Use LLM to classify the intent of a message and extract entities."""

    # Fast rule-based pre-classification for common patterns
    m = message.lower()
    if m.startswith("note:") or m.startswith("remember"):
        return {"intent": "save_note", "entities": {"content": message}, "confidence": 0.95}
    if m.startswith("todo:") or m.startswith("task:") or m.startswith("remind me"):
        return {"intent": "add_task", "entities": {"title": message.replace("todo:", "").replace("task:", "").strip()}, "confidence": 0.95}
    if "daily report" in m or "briefing" in m or "my status" in m:
        return {"intent": "daily_report", "entities": {}, "confidence": 0.95}
    if "follow-up" in m or "followup" in m or "follow up" in m:
        return {"intent": "get_followups", "entities": {}, "confidence": 0.9}
    if "pipeline" in m or "how is outreach" in m:
        return {"intent": "pipeline_status", "entities": {}, "confidence": 0.9}

    # LLM classification for everything else
    messages = [
        {"role": "system", "content": f"""You are an intent classifier for a founder's operating system.
Classify the user message into one of these intents: {', '.join(INTENTS)}
Extract any relevant entities (company names, person names, email addresses, etc.)
Respond ONLY with JSON like: {{"intent": "...", "entities": {{}}, "confidence": 0.0}}"""},
        {"role": "user", "content": message}
    ]
    raw = await complete(messages, task_type="general", max_tokens=200)
    clean = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        import json
        result = json.loads(clean)
        result["raw_message"] = message
        return result
    except Exception:
        return {"intent": "general_chat", "entities": {}, "confidence": 0.5, "raw_message": message}
```

### orchestrator/context.py
```python
from memory.vector_store import search_all
from memory.sql_store import search_contacts, search_companies, get_recent_outreach
import json

async def build_context(message: str, intent: str, entities: dict) -> str:
    """Build a rich context string to inject into LLM prompts."""
    sections = []

    # Semantic memory search
    memory_results = search_all(message, n_results=4)
    if memory_results:
        mem_texts = [f"- [{r['collection']}] {r['text'][:200]}" for r in memory_results]
        sections.append("RELEVANT MEMORY:\n" + "\n".join(mem_texts))

    # CRM context based on entities
    if entities.get("company"):
        companies = search_companies(entities["company"])
        if companies:
            c = companies[0]
            sections.append(f"CRM COMPANY CONTEXT:\nName: {c['name']}\nDescription: {c.get('description', '')}\nResearch: {c.get('research_summary', '')[:300]}")

    if entities.get("person") or entities.get("contact"):
        name = entities.get("person") or entities.get("contact")
        contacts = search_contacts(name)
        if contacts:
            c = contacts[0]
            sections.append(f"CRM CONTACT CONTEXT:\nName: {c['name']}, Role: {c.get('role', '')}, Company: {c.get('company', '')}, Status: {c.get('status', '')}, Notes: {c.get('notes', '')}")

    # Recent outreach for outreach-related intents
    if intent in ["draft_outreach", "send_email", "get_followups", "pipeline_status"]:
        recent = get_recent_outreach(days=14)
        if recent:
            lines = [f"- {r.get('contact_name', '?')} via {r['channel']} ({r['sent_at'][:10]}): {r.get('subject', '')}" for r in recent[:5]]
            sections.append("RECENT OUTREACH (14 days):\n" + "\n".join(lines))

    return "\n\n".join(sections) if sections else ""
```

### orchestrator/response_builder.py
```python
from orchestrator.router import classify_intent
from orchestrator.context import build_context
from agents.research_agent import research_company
from agents.outreach_agent import draft_email, draft_linkedin_message
from agents.memory_agent import save as mem_save, recall
from agents.crm_agent import (
    add as crm_add, update_status, get_followups,
    pipeline, search as crm_search, set_followup
)
from agents.report_agent import daily_briefing
from memory.sql_store import add_task, get_pending_tasks
from memory.vector_store import add as vec_add
from llm.router import complete
from tools.utils import format_contact, truncate
from config import config
import json

async def process_message(message: str) -> str:
    """Main entry point: process a user message and return a response string."""

    classified = await classify_intent(message)
    intent = classified.get("intent", "general_chat")
    entities = classified.get("entities", {})

    print(f"[Orchestrator] Intent: {intent} | Entities: {entities}")

    # Store conversation in memory
    vec_add("conversations", message, metadata={"role": "user", "intent": intent})

    try:

        # ── RESEARCH ──────────────────────────────────────────────────────────
        if intent == "research_company":
            company = entities.get("company") or _extract_after(message, ["research", "about", "find info on"])
            if not company:
                return "Which company should I research? Just say: *research [company name]*"
            await message_status(f"🔍 Researching {company}...")
            result = await research_company(company)
            s = result.get("summary", {})
            if isinstance(s, str):
                return truncate(s)
            lines = [
                f"*{s.get('name', company)}*",
                f"_{s.get('what_they_do', '')}_",
                "",
                f"🏭 Industry: {s.get('industry', '?')}",
                f"📍 Location: {s.get('location', '?')}",
                f"👥 Size: {s.get('size', '?')}",
                f"🌐 Website: {s.get('website', '?')}",
                "",
            ]
            if s.get("key_people"):
                lines.append("*Key People:*")
                for p in s["key_people"][:4]:
                    lines.append(f"  • {p.get('name')} — {p.get('role', '')}")
            if s.get("outreach_angle"):
                lines.append(f"\n💡 *Outreach angle:* {s['outreach_angle']}")
            return "\n".join(lines)

        # ── DRAFT OUTREACH ────────────────────────────────────────────────────
        elif intent == "draft_outreach":
            contact_name = entities.get("person") or entities.get("contact")
            company_name = entities.get("company")
            draft = await draft_email(contact_name=contact_name, company_name=company_name, custom_context=message)
            lines = [
                f"*Draft Email*",
                f"Subject: {draft.get('subject', '')}",
                "",
                draft.get("body", ""),
                "",
                "---",
                f"*LinkedIn variant:*",
                draft.get("linkedin_variant", ""),
                "",
                f"_{draft.get('personalization_notes', '')}_",
                "",
                "Reply *send* to send, or give me feedback to revise."
            ]
            return truncate("\n".join(lines))

        # ── ADD CONTACT ───────────────────────────────────────────────────────
        elif intent == "add_contact":
            name = entities.get("person") or entities.get("name")
            if not name:
                return "Who should I add? Try: *add John Smith, Head of Claims at HDFC Ergo, john@hdfc.com*"
            result = await crm_add(
                name=name,
                company=entities.get("company"),
                role=entities.get("role"),
                email=entities.get("email"),
                linkedin_url=entities.get("linkedin_url"),
            )
            return f"✅ {result['message']} (ID: {result['contact_id']})"

        # ── UPDATE CONTACT ────────────────────────────────────────────────────
        elif intent == "update_contact":
            contact = entities.get("person") or entities.get("contact")
            status = entities.get("status")
            if contact and status:
                result = await update_status(contact, status)
                return f"✅ {result.get('message', result.get('error', ''))}"
            return "Try: *mark [name] as responded* or *update [name] status to meeting_set*"

        # ── GET FOLLOWUPS ─────────────────────────────────────────────────────
        elif intent == "get_followups":
            contacts = await get_followups()
            if not contacts:
                return "✅ No follow-ups due right now. You're on top of it."
            lines = [f"*{len(contacts)} follow-ups due:*", ""]
            for c in contacts[:10]:
                lines.append(format_contact(c))
                lines.append("")
            return truncate("\n".join(lines))

        # ── PIPELINE STATUS ───────────────────────────────────────────────────
        elif intent == "pipeline_status":
            return await pipeline()

        # ── SAVE NOTE ─────────────────────────────────────────────────────────
        elif intent == "save_note":
            content = message.replace("note:", "").replace("remember that", "").replace("remember", "").strip()
            result = await mem_save(content, source="user_note")
            return f"✅ Saved to memory: _{content[:80]}_"

        # ── SEARCH MEMORY ─────────────────────────────────────────────────────
        elif intent == "search_memory":
            query = entities.get("query") or message
            results = await recall(query)
            if not results:
                return f"Nothing found in memory for: _{query}_"
            lines = [f"*Memory search: {query}*", ""]
            for r in results:
                lines.append(f"[{r['collection']}] {r['text'][:200]}")
                lines.append("")
            return truncate("\n".join(lines))

        # ── ADD TASK ──────────────────────────────────────────────────────────
        elif intent == "add_task":
            title = entities.get("title") or message.replace("todo:", "").replace("task:", "").replace("remind me to", "").strip()
            task_id = add_task(title=title)
            return f"✅ Task added: _{title}_ (ID: {task_id})"

        # ── GET TASKS ─────────────────────────────────────────────────────────
        elif intent == "get_tasks":
            tasks = get_pending_tasks()
            if not tasks:
                return "✅ No pending tasks. Clear queue!"
            lines = [f"*{len(tasks)} pending tasks:*", ""]
            for t in tasks[:10]:
                priority_icon = "🔴" if t["priority"] == 1 else "🟡" if t["priority"] == 2 else "🟢"
                due = f" (due {t['due_at'][:10]})" if t.get("due_at") else ""
                lines.append(f"{priority_icon} {t['title']}{due}")
            return "\n".join(lines)

        # ── DAILY REPORT ──────────────────────────────────────────────────────
        elif intent == "daily_report":
            await message_status("📊 Generating your briefing...")
            return await daily_briefing()

        # ── GENERAL CHAT ──────────────────────────────────────────────────────
        else:
            context = await build_context(message, intent, entities)
            messages = [
                {"role": "system", "content": f"""You are the personal AI operating system for {config.my_name}, {config.my_role} at {config.company_name}.
{config.company_name}: {config.my_one_liner}
You have full context of their business, contacts, and outreach. Be direct, smart, and immediately useful.
Use Telegram markdown formatting (* for bold, _ for italic).

{f"CONTEXT FROM MEMORY:{chr(10)}{context}" if context else ""}"""},
                {"role": "user", "content": message}
            ]
            response = await complete(messages, task_type="general")
            vec_add("conversations", response, metadata={"role": "assistant"})
            return truncate(response)

    except Exception as e:
        import traceback
        print(f"[Orchestrator Error] {e}\n{traceback.format_exc()}")
        return f"⚠️ Something went wrong: {str(e)[:200]}\n\nTry rephrasing or check the logs."

# Helpers
def _extract_after(text: str, keywords: list) -> str:
    text_lower = text.lower()
    for kw in keywords:
        idx = text_lower.find(kw)
        if idx != -1:
            return text[idx + len(kw):].strip()
    return ""

async def message_status(text: str):
    """Placeholder — bot handlers will send typing indicator instead."""
    print(f"[Status] {text}")
```

---

## STEP 8 — BOT LAYER

### bot/middleware.py
```python
from config import config

def is_authorized(user_id: int) -> bool:
    return user_id == config.my_telegram_user_id
```

### bot/formatters.py
```python
def split_long_message(text: str, max_len: int = 4000) -> list:
    """Split a long message into chunks for Telegram."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while len(text) > max_len:
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()
    if text:
        chunks.append(text)
    return chunks
```

### bot/handlers.py
```python
import logging
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, MessageHandler, CommandHandler, filters
from bot.middleware import is_authorized
from bot.formatters import split_long_message
from orchestrator.response_builder import process_message

logger = logging.getLogger(__name__)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    await update.message.reply_text(
        "👋 *Founder OS online.*\n\n"
        "I'm your personal executive assistant. Try:\n"
        "• `research [company name]`\n"
        "• `draft email to [person] at [company]`\n"
        "• `add [name] from [company] to CRM`\n"
        "• `who do I need to follow up with`\n"
        "• `show pipeline`\n"
        "• `daily report`\n"
        "• `note: [anything]`\n"
        "• Or just talk to me naturally.",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        logger.warning(f"Unauthorized access attempt from user_id={update.effective_user.id}")
        return

    user_message = update.message.text
    logger.info(f"Received: {user_message[:80]}")

    # Show typing indicator
    await ctx.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        response = await process_message(user_message)
        chunks = split_long_message(response)
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Handler error: {e}")
        await update.message.reply_text(f"⚠️ Error: {str(e)[:200]}")

def register_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
```

---

## STEP 9 — OUTREACH ENGINE

### outreach/email_sender.py
```python
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import config

logger = logging.getLogger(__name__)

def send_email(to_address: str, subject: str, body: str, reply_to: str = None) -> dict:
    """Send an email via Gmail SMTP."""
    if not config.gmail_address or not config.gmail_app_password:
        return {"success": False, "error": "Gmail not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env"}

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{config.my_name} <{config.gmail_address}>"
    msg["To"] = to_address
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(config.gmail_address, config.gmail_app_password)
            server.sendmail(config.gmail_address, to_address, msg.as_string())
        logger.info(f"Email sent to {to_address}: {subject}")
        return {"success": True, "to": to_address, "subject": subject}
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return {"success": False, "error": str(e)}
```

### outreach/tracker.py
```python
from memory.sql_store import log_outreach, get_recent_outreach, update_contact, search_contacts
from datetime import datetime, timedelta

def mark_sent(contact_name: str, channel: str, subject: str = None, body: str = None):
    contacts = search_contacts(contact_name)
    if not contacts:
        return {"error": f"Contact '{contact_name}' not found"}
    contact = contacts[0]
    log_id = log_outreach(contact["id"], channel=channel, direction="sent", subject=subject, body=body)
    followup_date = (datetime.now() + timedelta(days=3)).isoformat()
    update_contact(contact["id"], last_contacted_at=datetime.now().isoformat(),
                   status="contacted", next_followup_at=followup_date)
    return {"log_id": log_id, "contact": contact["name"], "followup_scheduled": followup_date[:10]}

def mark_responded(contact_name: str):
    contacts = search_contacts(contact_name)
    if not contacts:
        return {"error": f"Contact '{contact_name}' not found"}
    contact = contacts[0]
    update_contact(contact["id"], status="responded", next_followup_at=None, updated_at=datetime.now().isoformat())
    return {"message": f"{contact['name']} marked as responded"}

def get_campaign_status() -> dict:
    recent = get_recent_outreach(days=30)
    by_channel = {}
    for r in recent:
        ch = r.get("channel", "unknown")
        by_channel[ch] = by_channel.get(ch, 0) + 1
    return {"total_last_30_days": len(recent), "by_channel": by_channel, "recent": recent[:5]}
```

---

## STEP 10 — SCHEDULER

### scheduler/jobs.py
```python
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from agents.report_agent import daily_briefing
from memory.sql_store import get_contacts_needing_followup
from tools.utils import format_contact

logger = logging.getLogger(__name__)

_bot_app = None

def set_bot(app):
    global _bot_app
    _bot_app = app

async def send_to_user(text: str):
    from config import config
    if _bot_app and config.my_telegram_user_id:
        try:
            await _bot_app.bot.send_message(
                chat_id=config.my_telegram_user_id,
                text=text,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Scheduled message send failed: {e}")

async def job_daily_briefing():
    logger.info("[Scheduler] Running daily briefing job")
    try:
        briefing = await daily_briefing()
        await send_to_user(f"☀️ *Good morning!*\n\n{briefing}")
    except Exception as e:
        logger.error(f"Daily briefing job failed: {e}")

async def job_followup_reminder():
    logger.info("[Scheduler] Checking follow-ups")
    try:
        contacts = get_contacts_needing_followup()
        if contacts:
            lines = [f"🔔 *{len(contacts)} follow-up(s) due today:*", ""]
            for c in contacts[:5]:
                lines.append(f"• {c['name']} @ {c.get('company', '?')} (status: {c.get('status', '?')})")
            await send_to_user("\n".join(lines))
    except Exception as e:
        logger.error(f"Follow-up reminder job failed: {e}")

def start_scheduler(app) -> AsyncIOScheduler:
    set_bot(app)
    scheduler = AsyncIOScheduler()

    # Daily briefing at 8:00 AM
    scheduler.add_job(job_daily_briefing, CronTrigger(hour=8, minute=0), id="daily_briefing")

    # Follow-up reminder at 10:00 AM
    scheduler.add_job(job_followup_reminder, CronTrigger(hour=10, minute=0), id="followup_reminder")

    scheduler.start()
    logger.info("[Scheduler] Started. Daily briefing at 08:00, follow-up check at 10:00.")
    return scheduler
```

---

## STEP 11 — MAIN ENTRY POINT

### main.py
```python
import logging
import os
from telegram.ext import ApplicationBuilder
from bot.handlers import register_handlers
from scheduler.jobs import start_scheduler
from config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("./data/logs/founder_os.log") if os.path.exists("./data/logs") else logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    os.makedirs("./data/logs", exist_ok=True)
    os.makedirs("./data/chroma", exist_ok=True)

    logger.info(f"Starting Founder OS for {config.my_name} @ {config.company_name}")

    app = ApplicationBuilder().token(config.telegram_bot_token).build()
    register_handlers(app)
    start_scheduler(app)

    logger.info("Bot is running. Send a message on Telegram to start.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
```

---

### README.md
```markdown
# Founder OS — Personal AI Executive Assistant

Runs locally on your machine. Interface is Telegram. Free except LLM API calls (~₹100-200/month).

## Setup

1. Clone and enter the project
2. Create a virtual environment: `python -m venv venv && source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Copy config: `cp .env.example .env`
5. Fill in all values in `.env`
6. Run: `python main.py`

## Usage

Send messages to your Telegram bot:
- `research [company name]` — full company intelligence
- `draft email to [name] at [company]` — personalized outreach
- `add [name] from [company]` — add to CRM
- `mark [name] as responded` — update CRM status
- `who do I need to follow up with` — pending follow-ups
- `show pipeline` — pipeline summary
- `daily report` — full daily briefing
- `note: [anything]` — save to memory
- `search [query]` — search memory
- `todo: [task]` — add a task

## LLM Routing
- Groq (free) → Gemini Flash (free) → OpenAI GPT-4o-mini (paid fallback)

## Architecture
See the system diagram in the project documentation.
```

---

## 🔵 COMMIT 4
```
git add .
git commit -m "feat: orchestrator, bot handlers, outreach engine, scheduler, main entry point"
```
Tell the user: "Commit 4 done — full system built. Now installing dependencies and testing."

---

## STEP 12 — INSTALL AND TEST

Run these commands in the terminal:

```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

If any package fails to install, fix the version in requirements.txt and retry.

Then run:
```bash
python main.py
```

If it starts without errors and says "Bot is running", the system is working.

**Test by sending these messages to your Telegram bot in order:**

1. `/start` — should get the welcome message
2. `note: Testing Founder OS on [today's date]. First session.` — saves to memory
3. `research Bajaj Allianz` — triggers full research pipeline
4. `add Rahul Sharma, Head of Claims at HDFC Ergo, rahul@hdfcergo.com` — adds to CRM
5. `show pipeline` — shows pipeline summary
6. `daily report` — generates full briefing
7. `what do I know about HDFC Ergo` — tests memory recall

If any step fails, diagnose the error from the terminal logs and fix it.

---

## 🔵 COMMIT 5 (FINAL)
```
git add .
git commit -m "feat: complete Founder OS v1.0 — tested and working"
```
Tell the user:
```
✅ Founder OS is complete and running.

Everything is committed. Here's what you have:

• Telegram bot as your command interface
• Groq (free) → Gemini (free) → OpenAI fallback LLM chain
• ChromaDB vector memory (semantic search across everything)
• SQLite CRM with contacts, outreach log, companies, tasks, notes
• Research agent (web search + scraping + AI summarization)
• Outreach agent (personalized email and LinkedIn drafts)
• Email sending via Gmail SMTP
• Daily briefings at 8am + follow-up reminders at 10am (auto-scheduled)
• Everything runs locally — zero infra cost

To keep it running 24/7, run it on a Raspberry Pi or cheap VPS (optional).
To run in background: nohup python main.py > data/logs/run.log 2>&1 &
```

---

## IMPORTANT NOTES FOR THE AGENT

- Never use placeholder code like `# TODO implement this`. Everything must be fully implemented.
- If a library version causes a conflict, resolve it immediately and update requirements.txt.
- If any step produces an error during testing, fix it before moving to the next step.
- Always maintain the commit checkpoints exactly as written so the user has clean rollback points.
- The .env file must never be committed. Verify .gitignore covers it before every commit.
- All file paths are relative to the project root `founder-os/`.
- Python version required: 3.10 or higher. If the user is on an older version, tell them to upgrade before proceeding.