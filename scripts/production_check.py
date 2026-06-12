#!/usr/bin/env python3
"""Pre-deploy smoke: run tests and optional live HTTP checks against a running instance."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request


def run_pytest() -> int:
    print("==> Running pytest …")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"],
        cwd=None,
    )
    return proc.returncode


def _get(url: str) -> tuple[int, dict]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"error": body or e.reason}


def smoke_http(base: str) -> int:
    base = base.rstrip("/")
    print(f"==> HTTP smoke against {base} …")
    failures = 0

    code, body = _get(f"{base}/api/health")
    if code != 200 or not body.get("ok"):
        print(f"  FAIL /api/health → {code} {body}")
        failures += 1
    else:
        print(f"  OK   /api/health (storage={body.get('storage')})")

    code, body = _get(f"{base}/api/auth/status")
    if code != 200:
        print(f"  FAIL /api/auth/status → {code}")
        failures += 1
    else:
        print(
            f"  OK   /api/auth/status "
            f"(pin_required={body.get('pin_required')}, authenticated={body.get('authenticated')})"
        )

    code, body = _get(f"{base}/")
    if code != 200:
        print(f"  FAIL / → {code}")
        failures += 1
    else:
        print("  OK   / (index.html)")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Founder OS production readiness check")
    parser.add_argument(
        "--url",
        help="Optional base URL of a running instance (e.g. http://127.0.0.1:8787)",
    )
    parser.add_argument("--skip-tests", action="store_true", help="Only run HTTP smoke")
    args = parser.parse_args()

    exit_code = 0
    if not args.skip_tests:
        if run_pytest() != 0:
            exit_code = 1

    if args.url:
        if smoke_http(args.url) != 0:
            exit_code = 1

    if exit_code == 0:
        print("\nProduction check passed.")
    else:
        print("\nProduction check failed — fix issues above before deploying.", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
