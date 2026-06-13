import os
import tempfile

from memory import vault_documents as vd
from memory import world_repos as wr


def test_list_documents_for_github_repo_and_find_readme():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["VAULT_OBJECT_ROOT"] = tmp
        os.environ["FOUNDER_OS_DB"] = tempfile.mktemp(suffix=".db")
        os.environ.pop("AWS_S3_BUCKET", None)
        vd.init_vault_documents_db()
        wr.init_world_repos_db()

        vd.upsert_github_document(
            world_id="w1",
            world_slug="w1",
            template_id="startup",
            facet_id="docs",
            title="Root README",
            description="Project overview",
            filename="README.md",
            file_bytes=b"# Hello\n",
            source_ref="github:owner/repo:README.md",
            github_repo="owner/repo",
            github_path="README.md",
        )
        vd.upsert_github_document(
            world_id="w1",
            world_slug="w1",
            template_id="startup",
            facet_id="docs",
            title="Nested README",
            description="Package docs",
            filename="README.md",
            file_bytes=b"# Package\n",
            source_ref="github:owner/repo:pkg/README.md",
            github_repo="owner/repo",
            github_path="pkg/README.md",
        )
        vd.upsert_github_document(
            world_id="w1",
            world_slug="w1",
            template_id="startup",
            facet_id="docs",
            title="Other repo file",
            description="Different repo",
            filename="README.md",
            file_bytes=b"# Other\n",
            source_ref="github:owner/other:README.md",
            github_repo="owner/other",
            github_path="README.md",
        )

        docs = vd.list_documents_for_github_repo("w1", "owner/repo")
        assert len(docs) == 2
        assert all(d["github_repo"] == "owner/repo" for d in docs)

        readme = vd.find_readme_document(docs)
        assert readme is not None
        assert readme["github_path"] == "README.md"

        md_files = [d for d in docs if vd.is_markdown_path(d.get("github_path") or "")]
        assert len(md_files) == 2
