"""GitHub OAuth + API client for listing repos and fetching file contents."""
from __future__ import annotations

import json
import os
import secrets
import urllib.parse
from typing import Optional

import requests

from config import config

API_BASE = "https://api.github.com"


def token_path() -> str:
    return config.github_token_path


def is_connected() -> bool:
    return bool(get_access_token())


def get_access_token() -> Optional[str]:
    path = token_path()
    if not os.path.isfile(path):
        return None
    try:
        data = json.loads(open(path, encoding="utf-8").read())
        return data.get("access_token") or None
    except (json.JSONDecodeError, OSError):
        return None


def save_token(payload: dict) -> None:
    path = token_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def oauth_configured() -> bool:
    return bool(config.github_client_id and config.github_client_secret)


def build_auth_url(state: str = "") -> str:
    if not oauth_configured():
        raise RuntimeError("GitHub OAuth not configured — set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET")
    params = {
        "client_id": config.github_client_id,
        "redirect_uri": config.github_redirect_uri,
        "scope": "repo read:user",
        "state": state or secrets.token_urlsafe(16),
    }
    return "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)


def exchange_code(code: str) -> dict:
    if not oauth_configured():
        raise RuntimeError("GitHub OAuth not configured")
    r = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": config.github_client_id,
            "client_secret": config.github_client_secret,
            "code": code,
            "redirect_uri": config.github_redirect_uri,
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("error"):
        raise RuntimeError(data.get("error_description") or data["error"])
    return data


def _headers() -> dict:
    token = get_access_token()
    if not token:
        raise RuntimeError("GitHub not connected — authorize in Worlds → Knowledge graph")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def api_get(path: str, params: dict | None = None) -> dict | list:
    url = path if path.startswith("http") else f"{API_BASE}{path}"
    r = requests.get(url, headers=_headers(), params=params or {}, timeout=60)
    if r.status_code == 401:
        raise RuntimeError("GitHub token expired — reconnect GitHub")
    r.raise_for_status()
    return r.json()


def current_user() -> dict:
    return api_get("/user")


def list_repos(page: int = 1, per_page: int = 100, affiliation: str = "owner,collaborator,organization_member") -> list:
    return api_get(
        "/user/repos",
        {
            "page": page,
            "per_page": min(per_page, 100),
            "affiliation": affiliation,
            "sort": "updated",
            "direction": "desc",
        },
    )


def list_all_repos(max_pages: int = 5) -> list:
    repos = []
    for page in range(1, max_pages + 1):
        batch = list_repos(page=page)
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
    return repos


def get_repo(full_name: str) -> dict:
    owner, name = full_name.split("/", 1)
    return api_get(f"/repos/{owner}/{name}")


def list_repo_tree(full_name: str, branch: str | None = None) -> list:
    """Return blob paths (files) in repo via recursive git tree API."""
    owner, name = full_name.split("/", 1)
    meta = get_repo(full_name)
    ref = branch or meta.get("default_branch") or "main"
    commit = api_get(f"/repos/{owner}/{name}/git/ref/heads/{ref}")
    sha = commit["object"]["sha"]
    tree = api_get(f"/repos/{owner}/{name}/git/trees/{sha}", {"recursive": "1"})
    blobs = []
    for item in tree.get("tree") or []:
        if item.get("type") == "blob":
            blobs.append({"path": item["path"], "sha": item["sha"], "size": item.get("size") or 0})
    return blobs


def fetch_file_bytes(full_name: str, path: str, ref: str | None = None) -> bytes:
    import base64

    owner, name = full_name.split("/", 1)
    params = {"ref": ref} if ref else None
    data = api_get(f"/repos/{owner}/{name}/contents/{path}", params)
    if isinstance(data, list):
        raise RuntimeError(f"Path is a directory: {path}")
    content = data.get("content") or ""
    return base64.b64decode(content)
