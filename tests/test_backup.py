import os
import zipfile


def test_create_and_list_backup(tmp_path, monkeypatch):
    from agent import backup

    data = tmp_path / "data"
    data.mkdir()
    (data / "founder_os.db").write_text("dummy db")
    chroma = data / "chroma"
    chroma.mkdir()
    (chroma / "index.bin").write_text("vectors")
    bdir = data / "backups"

    monkeypatch.setattr(backup, "DATA_DIR", str(data))
    monkeypatch.setattr(backup, "BACKUP_DIR", str(bdir))

    res = backup.create_backup()
    assert res["created"] is True
    assert res["files"] >= 2
    assert os.path.exists(res["path"])

    with zipfile.ZipFile(res["path"]) as zf:
        names = zf.namelist()
    assert any("founder_os.db" in n for n in names)
    # The backups dir itself must never be inside the archive.
    assert not any("backups" in n for n in names)

    listing = backup.list_backups()
    assert listing["count"] == 1


def test_prune_keeps_only_recent(tmp_path, monkeypatch):
    from agent import backup

    data = tmp_path / "data"
    data.mkdir()
    (data / "founder_os.db").write_text("x")
    bdir = data / "backups"
    monkeypatch.setattr(backup, "DATA_DIR", str(data))
    monkeypatch.setattr(backup, "BACKUP_DIR", str(bdir))
    monkeypatch.setattr(backup, "KEEP", 3)

    for _ in range(5):
        backup.create_backup()
    assert backup.list_backups()["count"] <= 3
