"""Central data directory — set FOUNDER_OS_DATA on EC2 for persistent EBS storage."""
from __future__ import annotations

import os
from pathlib import Path

_SUBDIRS = (
    "logs",
    "knowledge",
    "vault-objects",
    "backups",
    "documents",
    "traces",
    "agent_state",
    "world_state",
    "evals",
)


def data_root() -> Path:
    return Path(os.getenv("FOUNDER_OS_DATA", "./data")).resolve()


def subpath(*parts: str) -> Path:
    return data_root().joinpath(*parts)


def ensure_data_dirs() -> Path:
    root = data_root()
    for name in _SUBDIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
    return root
