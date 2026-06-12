"""Infrastructure health probes — EC2 metadata, S3 vault, disk (Settings monitor)."""
from __future__ import annotations

import os
import shutil
import time
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

_IMDS_BASE = "http://169.254.169.254/latest/meta-data"
_IMDS_TOKEN_URL = "http://169.254.169.254/latest/api/token"
_PROBE_KEY = "_healthcheck/settings-probe.txt"
_TIMEOUT = 2.5


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _imds_token() -> Optional[str]:
    try:
        req = Request(
            _IMDS_TOKEN_URL,
            method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
        )
        with urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read().decode("utf-8").strip() or None
    except (OSError, URLError, TimeoutError):
        return None


def _imds_get(path: str, token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    try:
        req = Request(
            f"{_IMDS_BASE}/{path.lstrip('/')}",
            headers={"X-aws-ec2-metadata-token": token},
        )
        with urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read().decode("utf-8").strip() or None
    except (OSError, URLError, TimeoutError):
        return None


def _ec2_host() -> dict[str, Any]:
    token = _imds_token()
    instance_id = _imds_get("instance-id", token)
    if not instance_id:
        return {"platform": "local", "ok": True, "detail": "Not running on EC2 (dev or non-AWS host)"}
    role_raw = _imds_get("iam/security-credentials/", token) or ""
    role_name = role_raw.splitlines()[0].strip() if role_raw else ""
    return {
        "platform": "ec2",
        "ok": True,
        "instance_id": instance_id,
        "region": _imds_get("placement/region", token),
        "instance_type": _imds_get("instance-type", token),
        "availability_zone": _imds_get("placement/availability-zone", token),
        "iam_role": role_name or None,
    }


def _disk_usage() -> dict[str, Any]:
    data_root = os.getenv("FOUNDER_OS_DATA", "./data")
    try:
        usage = shutil.disk_usage(data_root)
        free_gb = round(usage.free / (1024 ** 3), 2)
        total_gb = round(usage.total / (1024 ** 3), 2)
        used_pct = round((usage.used / usage.total) * 100, 1) if usage.total else 0
        ok = free_gb >= 0.5
        return {
            "ok": ok,
            "path": data_root,
            "free_gb": free_gb,
            "total_gb": total_gb,
            "used_pct": used_pct,
            "detail": "Low disk space" if not ok else "OK",
        }
    except OSError as e:
        return {"ok": False, "path": data_root, "detail": str(e)}


def _s3_status(probe_write: bool = True) -> dict[str, Any]:
    from integrations import object_storage

    bucket = os.getenv("AWS_S3_BUCKET", "").strip()
    region = os.getenv("AWS_REGION", "").strip() or None
    if not bucket:
        return {
            "configured": False,
            "ok": False,
            "detail": "Set AWS_S3_BUCKET in environment",
        }

    out: dict[str, Any] = {
        "configured": True,
        "bucket": bucket,
        "region": region,
        "ok": False,
        "reachable": False,
        "read_write_ok": False,
    }

    try:
        import boto3

        client = object_storage._s3_client()
        client.head_bucket(Bucket=bucket)
        out["reachable"] = True
    except ImportError:
        out["detail"] = "boto3 not installed"
        return out
    except Exception as e:
        out["detail"] = f"Bucket unreachable: {e}"
        return out

    if not probe_write:
        out["ok"] = True
        out["detail"] = "Bucket reachable"
        return out

    token = f"probe-{int(time.time())}"
    payload = f"nawab-os-probe:{token}".encode("utf-8")
    try:
        put = object_storage.put_bytes(_PROBE_KEY, payload, "text/plain")
        if put.get("error"):
            out["detail"] = put["error"]
            return out
        if put.get("backend") != "s3":
            out["detail"] = f"Expected S3 backend, got {put.get('backend')}"
            return out
        got = object_storage.get_bytes(_PROBE_KEY)
        if got != payload:
            out["detail"] = "Read after write failed"
            return out
        object_storage.delete_object(_PROBE_KEY)
        out["read_write_ok"] = True
        out["ok"] = True
        out["detail"] = "Read/write OK"
    except Exception as e:
        out["detail"] = str(e)
    return out


def collect(probe_s3_write: bool = True) -> dict[str, Any]:
    from integrations import object_storage

    host = _ec2_host()
    s3 = _s3_status(probe_write=probe_s3_write)
    disk = _disk_usage()
    storage_backend = "s3" if object_storage.s3_enabled() else "local"

    overall_ok = (
        host.get("ok", False)
        and disk.get("ok", False)
        and (s3.get("ok", False) if s3.get("configured") else True)
    )

    return {
        "checked_at": _utc_now(),
        "ok": overall_ok,
        "app": {
            "ok": True,
            "storage_backend": storage_backend,
            "public_url": os.getenv("PUBLIC_BASE_URL", "").strip() or None,
        },
        "host": host,
        "s3": s3,
        "disk": disk,
    }
