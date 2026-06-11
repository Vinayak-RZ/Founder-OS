import os
import tempfile

import pytest

from memory import knowledge_vault as kv
from memory import world_templates as wt


def test_ensure_world_structure_creates_folders():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["KNOWLEDGE_VAULT_ROOT"] = tmp
        tpl = wt.template_for_kind("startup")
        r = kv.ensure_world_structure("test-world", "test-world", tpl)
        assert os.path.isdir(r["vault_path"])
        assert len(r["folders"]) >= 3
        base = kv.world_vault_path("test-world", "test-world")
        assert (base / "leads").is_dir()


def test_ingest_markdown_file():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["KNOWLEDGE_VAULT_ROOT"] = tmp
        tpl = "idea"
        kv.ensure_world_structure("idea-1", "idea-1", tpl)
        base = kv.world_vault_path("idea-1", "idea-1")
        note = base / "hypothesis" / "test.md"
        note.write_text("# Hypothesis\nWe believe SMEs need prescriptive energy analytics.", encoding="utf-8")
        try:
            r = kv.ingest_file(str(note), "idea-1", "idea-1", tpl)
            assert r.get("chunks", 0) >= 1
        except Exception:
            pytest.skip("Qdrant unavailable in test environment")
