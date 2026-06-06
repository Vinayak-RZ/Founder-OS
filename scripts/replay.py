"""Replay a recorded turn from the trace log.

Usage:
  python scripts/replay.py                 # show today's recent traces
  python scripts/replay.py <trace_id>      # print full trace detail
  python scripts/replay.py <trace_id> --run  # re-run the same input through the agent

Re-running executes real tools, so use --run with care (sending is still gated).
"""
import asyncio
import glob
import json
import os
import sys

TRACE_DIR = "./data/traces"


def _all_records():
    records = []
    for path in sorted(glob.glob(os.path.join(TRACE_DIR, "*.jsonl"))):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


def _find(trace_id):
    for r in _all_records():
        if r.get("id") == trace_id:
            return r
    return None


def _print_detail(rec):
    print(f"Trace {rec['id']} | actor={rec['actor']} | {rec['duration_s']}s")
    print(f"USER: {rec['message']}\n")
    for e in rec["events"]:
        if e["type"] == "tool":
            d = e["data"]
            print(f"  [{e['t']}s] TOOL {d['name']} ({d['decision']}) -> {d['result_preview'][:160]}")
        elif e["type"] == "llm":
            d = e["data"]
            print(f"  [{e['t']}s] LLM {d.get('model')} tok={d.get('prompt_tokens')}/{d.get('completion_tokens')}")
        elif e["type"] == "plan":
            print(f"  [{e['t']}s] PLAN {e['data']}")
    print(f"\nFINAL: {rec['final']}")


async def _rerun(rec):
    from agent import core
    print("\n=== RE-RUNNING ===")
    out = await core.run(rec["message"], actor="replay")
    print(out)


def main():
    args = [a for a in sys.argv[1:]]
    if not args:
        for r in _all_records()[-10:]:
            tools = [e["data"]["name"] for e in r["events"] if e["type"] == "tool"]
            print(f"{r['id']}  {r['actor']:9} {r['duration_s']:>5}s  tools={tools}  | {r['message'][:60]}")
        return
    trace_id = args[0]
    rec = _find(trace_id)
    if not rec:
        print(f"No trace with id {trace_id}")
        return
    _print_detail(rec)
    if "--run" in args:
        asyncio.run(_rerun(rec))


if __name__ == "__main__":
    main()
