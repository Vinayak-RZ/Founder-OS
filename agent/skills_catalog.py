"""Curated Cursor/agent skills the platform knows about.

These are playbooks the supervisor and specialists can reference. Deep execution
may happen in Cursor/Claude; Founder OS coordinates and surfaces results.
"""
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

CURATED_SKILLS = [
    {
        "id": "industry-analysis",
        "name": "Industry analysis",
        "path": ".cursor/skills/industry-analysis/SKILL.md",
        "agents": ["market", "vault"],
        "summary": "Structured industry sizing, value chain, and competitive landscape analysis.",
    },
    {
        "id": "lead-generation",
        "name": "Lead generation",
        "path": ".cursor/skills/lead-generation/SKILL.md",
        "agents": ["leads", "outreach"],
        "summary": "ICP definition, prospect research, and outreach list building.",
    },
]


def list_skills() -> list:
    out = []
    for s in CURATED_SKILLS:
        item = dict(s)
        full = _PROJECT_ROOT / s["path"]
        item["installed"] = full.is_file()
        out.append(item)
    return out


def prompt_block() -> str:
    lines = [
        "Founder OS is an AGGREGATOR — it tracks parallel projects, links repos/docs, "
        "queries the knowledge vault, and runs outreach. Deep research and coding happen "
        "in Cursor/Claude; you coordinate and surface status.",
        "",
        "Curated skills (reference when delegating or advising):",
    ]
    for s in list_skills():
        flag = "installed" if s["installed"] else "missing"
        agents = ", ".join(s.get("agents") or [])
        lines.append(f"- {s['name']} [{flag}] → specialists: {agents}. {s['summary']}")
    return "\n".join(lines)
