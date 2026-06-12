"""Background agent jobs for the web UI — async chat/delegate without HTTP timeouts."""
from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}
_MAX_JOBS = 80


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _public(job: dict) -> dict:
    return {
        "id": job["id"],
        "status": job["status"],
        "mode": job.get("mode"),
        "specialist": job.get("specialist"),
        "world_id": job.get("world_id"),
        "message": job.get("message", "")[:500],
        "phase": job.get("phase") or "",
        "events": list(job.get("events") or [])[-40:],
        "result": job.get("result"),
        "error": job.get("error"),
        "session_id": job.get("session_id"),
        "run_id": job.get("run_id"),
        "artifacts": job.get("artifacts") or [],
        "active": job["status"] == "running",
        "elapsed_s": round(time.time() - job["started_at"], 1) if job.get("started_at") else 0,
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
    }


def _append_event(job: dict, etype: str, label: str, **extra) -> None:
    job["events"].append({
        "t": round(time.time() - (job.get("started_at") or time.time()), 2),
        "type": etype,
        "label": label,
        **extra,
    })
    job["events"] = job["events"][-40:]
    job["phase"] = label


def _set_status(job: dict, status: str, **fields) -> None:
    job["status"] = status
    job.update(fields)
    if status in ("completed", "failed", "cancelled"):
        job["finished_at"] = time.time()


def _cleanup_old() -> None:
    if len(_jobs) <= _MAX_JOBS:
        return
    finished = sorted(
        [(jid, j) for jid, j in _jobs.items() if j.get("status") != "running"],
        key=lambda x: x[1].get("finished_at") or 0,
    )
    for jid, _ in finished[: max(0, len(_jobs) - _MAX_JOBS)]:
        _jobs.pop(jid, None)


def is_cancelled(job_id: str) -> bool:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return True
        ev = job.get("cancel_event")
        return bool(ev and ev.is_set())


def cancel_job(job_id: str) -> bool:
    with _lock:
        job = _jobs.get(job_id)
        if not job or job.get("status") != "running":
            return False
        ev = job.get("cancel_event")
        if ev:
            ev.set()
        _set_status(job, "cancelled", phase="Stopping…")
        return True


def get_job(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        return _public(job) if job else None


def list_jobs(active_only: bool = False) -> list[dict]:
    with _lock:
        items = list(_jobs.values())
    if active_only:
        items = [j for j in items if j.get("status") == "running"]
    items.sort(key=lambda j: j.get("started_at") or 0, reverse=True)
    return [_public(j) for j in items[:30]]


def start_job(
    *,
    mode: str,
    message: str,
    world_id: str | None = None,
    rag_mode: str = "auto",
    specialist: str = "supervisor",
    session_id: str | None = None,
) -> dict:
    job_id = _new_id()
    cancel_event = threading.Event()
    job = {
        "id": job_id,
        "status": "queued",
        "mode": mode,
        "message": message,
        "world_id": world_id,
        "rag_mode": rag_mode,
        "specialist": specialist,
        "session_id": session_id,
        "run_id": None,
        "phase": "Queued…",
        "events": [],
        "result": None,
        "error": None,
        "artifacts": [],
        "cancel_event": cancel_event,
        "started_at": time.time(),
        "finished_at": None,
    }
    with _lock:
        _jobs[job_id] = job
        _cleanup_old()

    thread = threading.Thread(target=_run_job_thread, args=(job_id,), daemon=True)
    thread.start()
    return _public(job)


def _run_job_thread(job_id: str) -> None:
    try:
        asyncio.run(_run_job_async(job_id))
    except Exception as e:
        logger.exception("agent job %s crashed", job_id)
        with _lock:
            job = _jobs.get(job_id)
            if job and job.get("status") == "running":
                _set_status(job, "failed", error=str(e)[:500], phase="Failed")


async def _run_job_async(job_id: str) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        _set_status(job, "running", phase="Starting…")
        _append_event(job, "phase", "Starting…")

    from dashboard import live_ops
    from memory import agent_history

    message = job["message"]
    world_id = job.get("world_id")
    rag_mode = job.get("rag_mode") or "auto"
    specialist = job.get("specialist") or "supervisor"
    mode = job.get("mode") or "chat"
    title = message[:80] + ("…" if len(message) > 80 else "")

    session_id = agent_history.begin_turn(
        session_id=job.get("session_id"),
        world_id=world_id,
        specialist=specialist if mode == "delegate" else "supervisor",
        title=title,
    )
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job["session_id"] = session_id
    agent_history.add_message(session_id, "user", message)

    def should_cancel() -> bool:
        return is_cancelled(job_id)

    async def on_status(text: str) -> None:
        with _lock:
            j = _jobs.get(job_id)
            if not j or j.get("status") != "running":
                return
            _append_event(j, "phase", text)
        live_ops.set_phase(text)

    actor_label = f"subagent:{specialist}" if mode == "delegate" else "user"
    live_ops.begin(actor_label, message)

    reply = ""
    try:
        if should_cancel():
            reply = "⏹ Stopped before start."
        elif mode == "delegate":
            from agent import subagent, trace

            trace.start(f"subagent:{specialist}", message)
            out = await subagent.run_subagent(
                specialist,
                message,
                actor="user",
                on_status=on_status,
                world_id=world_id,
                should_cancel=should_cancel,
            )
            if should_cancel():
                reply = "⏹ Stopped by user."
            else:
                reply = str(out.get("result") or out.get("error") or "")
            trace.finish(reply)
        else:
            from agent import core

            reply = await core.run(
                message,
                actor="user",
                on_status=on_status,
                world_id=world_id,
                rag_mode=rag_mode,
                should_cancel=should_cancel,
            )
            if should_cancel() and not reply.startswith("⏹"):
                reply = "⏹ Stopped by user."
    except Exception as e:
        logger.exception("agent job %s failed", job_id)
        with _lock:
            j = _jobs.get(job_id)
            if j:
                _set_status(j, "failed", error=str(e)[:500], phase="Failed")
                _append_event(j, "phase", f"Failed: {str(e)[:120]}")
        live_ops.end()
        agent_history.end_turn()
        return
    finally:
        live_ops.end()

    run_id = agent_history.current_run_id()
    if reply and not should_cancel():
        agent_history.add_message(session_id, "assistant", reply, run_id=run_id)
    elif should_cancel():
        agent_history.add_message(session_id, "system", "⏹ Stopped by user.", run_id=run_id)

    artifacts = []
    try:
        if run_id:
            artifacts = agent_history.list_artifacts(run_id=run_id)
    except Exception:
        pass

    with _lock:
        j = _jobs.get(job_id)
        if not j:
            agent_history.end_turn()
            return
        j["run_id"] = run_id
        j["artifacts"] = artifacts
        j["result"] = reply
        if should_cancel():
            _set_status(j, "cancelled", phase="Stopped")
            _append_event(j, "phase", "Stopped by user")
        else:
            _set_status(j, "completed", phase="Complete")
            _append_event(j, "phase", "Complete")

    agent_history.end_turn()


def live_snapshot() -> dict:
    """Merged view for /api/live — active jobs + legacy single-op state."""
    from dashboard import live_ops

    base = live_ops.snapshot()
    jobs = list_jobs(active_only=True)
    base["jobs"] = jobs
    base["active_jobs"] = len(jobs)
    if jobs and not base.get("active"):
        top = jobs[0]
        base["active"] = True
        base["actor"] = top.get("specialist") or top.get("mode") or "agent"
        base["phase"] = top.get("phase") or "Working…"
        base["events"] = top.get("events") or []
    return base
