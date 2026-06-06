"""Strategy optimizer — lightweight online experimentation.

The agent can register the outcome of an approach it tried (a "variant" within a
decision "group", e.g. an email-subject style or an outreach time-of-day) and
later ask which approach has worked best. Selection uses epsilon-greedy over the
observed success rate: mostly exploit the best, occasionally explore. This is a
practical, dependency-free stand-in for DSPy-style prompt/strategy optimization.
"""
import random

from agent import store


def record(group: str, variant: str, success: bool):
    store.record_strategy(group, variant, success)


def leaderboard(group: str) -> list:
    rows = store.strategy_leaderboard(group)
    for r in rows:
        trials = max(r.get("trials", 0), 1)
        r["success_rate"] = round(r.get("successes", 0) / trials, 3)
    return rows


def choose(group: str, variants: list, epsilon: float = 0.2) -> str:
    """Pick a variant: explore unseen ones first, else epsilon-greedy on rate."""
    if not variants:
        return ""
    board = {r["variant"]: r for r in leaderboard(group)}
    unseen = [v for v in variants if v not in board]
    if unseen:
        return random.choice(unseen)
    if random.random() < epsilon:
        return random.choice(variants)
    best = max(variants, key=lambda v: board.get(v, {}).get("success_rate", 0.0))
    return best


def top_strategies(limit: int = 8) -> str:
    """Render the most-tried strategies for prompt injection."""
    rows = store.all_strategies(limit)
    if not rows:
        return ""
    lines = []
    for r in rows:
        trials = max(r.get("trials", 0), 1)
        rate = round(r.get("successes", 0) / trials, 2)
        lines.append(f"- [{r['grp']}] '{r['variant']}': {rate} success over {r['trials']} tries")
    return "\n".join(lines)
