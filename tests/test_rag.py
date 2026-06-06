from agent.tools import rag_tools


def test_chunk_empty_returns_empty():
    assert rag_tools._chunk("") == []
    assert rag_tools._chunk("   ") == []


def test_chunk_splits_long_text():
    chunks = rag_tools._chunk("word " * 1000, size=200, overlap=20)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)


def test_chunk_terminates_and_covers():
    chunks = rag_tools._chunk("a" * 1000, size=100, overlap=10)
    assert len(chunks) >= 10
    assert "".join(chunks).startswith("a" * 100)
