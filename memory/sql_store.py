import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional

# DB path is env-overridable so tests (and alternate deployments) can point at an
# isolated database instead of the live one.
DB_PATH = os.getenv("FOUNDER_OS_DB", "./data/founder_os.db")
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

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
    c.execute("""INSERT INTO outreach_log (contact_id, channel, direction, subject, body, status, sent_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
              (contact_id, channel, direction, subject, body, status, datetime.now().isoformat()))
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
