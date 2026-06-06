"""Self-eval runner — safe, side-effect-free behavior regression tests.

For each scenario we run a SINGLE model decision (one tool-calling completion) and
inspect which tools the model chose. We never execute the tools, so running evals
has no side effects (no emails sent, no CRM writes). Results are appended to
data/evals/history.jsonl so you can watch the pass rate as the agent self-evolves.

Run:  python -m evals.runner
"""
import asyncio
import json
import os
import time

from agent import registry, identity
import agent.tools  # noqa: F401 — register tools
from llm.tool_client import complete_with_tools
from evals.scenarios import SCENARIOS

HISTORY_PATH = "./data/evals/history.jsonl"


async def _called_tools(message: str) -> list:
    system = identity.build_system_prompt()
    messages = [{"role": "system", "content": system}, {"role": "user", "content": message}]
    try:
        resp = await complete_with_tools(messages, registry.all_schemas())
    except Exception as e:
        return [f"__error__:{e}"]
    return [tc["name"] for tc in (resp.get("tool_calls") or [])]


async def run_all(verbose: bool = True) -> dict:
    results = []
    for sc in SCENARIOS:
        called = await _called_tools(sc["message"])
        expect_any = sc.get("expect_any") or []
        forbid = sc.get("forbid") or []
        hit_expected = (not expect_any) or any(t in called for t in expect_any)
        hit_forbidden = any(t in called for t in forbid)
        passed = hit_expected and not hit_forbidden
        results.append({"name": sc["name"], "passed": passed, "called": called,
                        "expect_any": expect_any})
        if verbose:
            mark = "PASS" if passed else "FAIL"
            print(f"[{mark}] {sc['name']}: called={called} expected_any={expect_any}")

    passed = sum(1 for r in results if r["passed"])
    summary = {"ts": time.time(), "total": len(results), "passed": passed,
               "pass_rate": round(passed / max(len(results), 1), 3), "results": results}

    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(summary) + "\n")

    if verbose:
        print(f"\nPASS RATE: {passed}/{len(results)} ({summary['pass_rate']*100:.0f}%)")
    return summary


if __name__ == "__main__":
    asyncio.run(run_all())
