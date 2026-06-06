import os

from agent.tools import document_tools


def test_safe_filename_sanitizes():
    name = document_tools._safe_filename("My Report!! / draft")
    assert " " not in name
    assert "/" not in name
    assert name.startswith("My_Report")


def test_latin1_replaces_unicode_without_error():
    out = document_tools._latin1("smart \u201cquote\u201d and emoji \U0001F600")
    out.encode("latin-1")  # must not raise


def test_write_pdf_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr(document_tools, "DOCS_DIR", str(tmp_path))
    path, fmt = document_tools._write_pdf("doc", "Title", "Body text\nSecond line")
    assert os.path.exists(path)
    assert fmt in ("pdf", "txt")
    assert os.path.getsize(path) > 0
