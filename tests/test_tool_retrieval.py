"""Tool-RAG unit tests.

We monkeypatch the embedding query (`relevant_tool_names`) so tests are fast and
deterministic and don't require the local embedding model.
"""
import agent.tools  # noqa: F401 — register the full tool catalog
from agent import tool_retrieval, registry
from config import config


def _names(schemas):
    return {s["function"]["name"] for s in schemas}


def test_core_tools_always_included(monkeypatch):
    monkeypatch.setattr(config, "tool_rag", True)
    monkeypatch.setattr(tool_retrieval, "relevant_tool_names",
                        lambda msg, k: {"set_reminder"})
    names = _names(tool_retrieval.schemas_for_message("remind me later", k=5))
    # the retrieved tool plus the always-on core set
    assert "set_reminder" in names
    assert {"search_memory", "deep_recall", "world_state"}.issubset(names)


def test_subset_smaller_than_full_catalog(monkeypatch):
    monkeypatch.setattr(config, "tool_rag", True)
    monkeypatch.setattr(tool_retrieval, "relevant_tool_names",
                        lambda msg, k: {"draft_email", "send_email"})
    subset = _names(tool_retrieval.schemas_for_message("email this lead", k=5))
    full = _names(registry.all_schemas())
    assert subset.issubset(full)
    assert len(subset) < len(full)


def test_fallback_to_full_catalog_when_retrieval_empty(monkeypatch):
    monkeypatch.setattr(config, "tool_rag", True)
    # Force CORE to be empty so the <4 safety fallback triggers on empty retrieval.
    monkeypatch.setattr(tool_retrieval, "_CORE", set())
    monkeypatch.setattr(tool_retrieval, "relevant_tool_names", lambda msg, k: set())
    out = tool_retrieval.schemas_for_message("anything", k=5)
    assert len(out) == len(registry.all_schemas())


def test_disabled_returns_full_catalog(monkeypatch):
    monkeypatch.setattr(config, "tool_rag", False)
    out = tool_retrieval.schemas_for_message("hello", k=5)
    assert len(out) == len(registry.all_schemas())
