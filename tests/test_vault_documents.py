import os
import tempfile

import pytest

from memory import vault_documents as vd
from integrations import object_storage


def test_create_and_list_document_local_storage():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["VAULT_OBJECT_ROOT"] = tmp
        os.environ.pop("AWS_S3_BUCKET", None)
        vd.init_vault_documents_db()
        doc = vd.create_document(
            "test-world",
            "test-world",
            "startup",
            "clients",
            "Current ICP",
            "SMB manufacturers in EU seeking energy analytics",
            text_content="# ICP\n\nSMB manufacturers…",
        )
        assert doc["id"]
        assert doc["title"] == "Current ICP"
        assert doc["facet_id"] == "clients"
        listed = vd.list_documents("test-world", "clients")
        assert len(listed) == 1
        raw = object_storage.get_bytes(doc["storage_key"])
        assert raw and b"ICP" in raw


def test_update_and_delete_document():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["VAULT_OBJECT_ROOT"] = tmp
        os.environ.pop("AWS_S3_BUCKET", None)
        vd.init_vault_documents_db()
        doc = vd.create_document(
            "w2", "w2", "research", "notes", "Paper notes", "Initial",
            text_content="# Notes\nv1",
        )
        updated = vd.update_document(
            doc["id"],
            title="Paper notes v2",
            description="Updated summary",
            text_content="# Notes\nv2",
            template_id="research",
        )
        assert updated["title"] == "Paper notes v2"
        assert vd.delete_document(doc["id"])
        assert vd.get_document(doc["id"]) is None


def test_effective_facets_uses_template():
    facets = vd.effective_facets({}, "startup")
    assert any(f.get("id") == "clients" for f in facets)
