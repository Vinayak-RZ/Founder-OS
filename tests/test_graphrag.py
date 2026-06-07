import asyncio

from memory import graphrag, graph


def test_detect_communities_splits_two_clusters():
    # Two triangles connected by nothing -> two communities.
    edges = [
        ("A", "knows", "B"), ("B", "knows", "C"), ("A", "knows", "C"),
        ("X", "knows", "Y"), ("Y", "knows", "Z"), ("X", "knows", "Z"),
    ]
    comms = graphrag.detect_communities(edges)
    groups = sorted([sorted(m) for m in comms.values()], key=len, reverse=True)
    flat = {frozenset(g) for g in groups}
    assert frozenset({"A", "B", "C"}) in flat
    assert frozenset({"X", "Y", "Z"}) in flat


def test_detect_communities_empty():
    assert graphrag.detect_communities([]) == {}


def test_rank_communities_prefers_overlap():
    comms = [
        {"summary": "fintech investors and banking contacts", "members": ["Acme Bank"], "size": 3},
        {"summary": "healthcare clinic partners", "members": ["MedCo"], "size": 2},
    ]
    ranked = graphrag._rank_communities("who do I know in fintech and banking?", comms)
    assert "fintech" in ranked[0]["summary"]


def test_global_answer_builds_then_answers(monkeypatch):
    monkeypatch.setattr(graphrag, "list_communities", lambda: [
        {"label": "1", "size": 3, "summary": "fintech cluster",
         "members": ["A", "B", "C"]}])

    async def fake_complete(messages, task_type="general", max_tokens=400):
        return "Your network centers on a fintech cluster."
    monkeypatch.setattr("llm.router.complete", fake_complete)

    out = asyncio.run(graphrag.global_answer("what is my network about?"))
    assert "fintech" in out["answer"].lower()
    assert out["communities"]
