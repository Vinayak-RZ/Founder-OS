import os
import tempfile

from memory import world_repos as wr


def test_add_list_remove_repo():
    os.environ["FOUNDER_OS_DB"] = tempfile.mktemp(suffix=".db")
    wr.init_world_repos_db()
    link = wr.add_repo("world-a", "owner/my-repo", default_branch="main", private=True)
    assert link["full_name"] == "owner/my-repo"
    repos = wr.list_repos("world-a")
    assert len(repos) == 1
    wr.update_repo_sync(link["id"], 5, "")
    updated = wr.get_repo_link(link["id"])
    assert updated["file_count"] == 5
    assert wr.remove_repo(link["id"], "world-a")
    assert wr.list_repos("world-a") == []
