"""Tests for batched GitHub sync jobs."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

import integrations.github_sync as gs
from memory import sync_jobs as sj


def _env_db(monkeypatch):
    path = tempfile.mktemp(suffix=".db")
    monkeypatch.setenv("FOUNDER_OS_DB", path)
    return path


def test_sync_job_create_and_batch(monkeypatch):
    _env_db(monkeypatch)
    sj.init_sync_jobs_db()
    job = sj.create_job(
        world_id="w1",
        link_id=1,
        full_name="owner/repo",
        branch="main",
        world_slug="w1",
        template_id="startup",
        manifest=[{"path": "README.md", "size": 100}, {"path": "docs/a.md", "size": 50}],
    )
    assert job["total_files"] == 2
    view = sj.public_view(job["id"])
    assert view["status"] == "pending"
    assert view["progress"] == 0.0


def test_process_batch_imports_files(monkeypatch):
    _env_db(monkeypatch)
    sj.init_sync_jobs_db()
    job = sj.create_job(
        world_id="w1",
        link_id=7,
        full_name="owner/repo",
        branch="main",
        world_slug="slug",
        template_id="startup",
        manifest=[{"path": "README.md", "size": 20}],
    )

    with patch.object(gs, "import_file") as imp:
        with patch("memory.world_repos.update_repo_sync") as upd:
            with patch("dashboard.notifications.push"):
                result = gs.process_sync_batch(job["id"], batch_size=5)

    imp.assert_called_once()
    upd.assert_called_once()
    assert result["done"] is True
    assert result["imported"] == 1


def test_start_job_manifest_failure(monkeypatch):
    _env_db(monkeypatch)
    sj.init_sync_jobs_db()
    with patch.object(gs, "build_file_manifest", side_effect=RuntimeError("GitHub API down")):
        with patch("dashboard.notifications.push"):
            view = gs.start_repo_sync_job(
                world_id="w1",
                world_slug="slug",
                template_id="startup",
                full_name="owner/big",
                branch="main",
                link_id=3,
            )
    assert view["status"] == "failed"
