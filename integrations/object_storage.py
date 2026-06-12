"""Object storage for large vault documents — S3 when configured, else local mirror."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

def _local_root() -> Path:
    default = os.getenv("FOUNDER_OS_DATA", "./data")
    return Path(os.getenv("VAULT_OBJECT_ROOT", f"{default}/vault-objects")).resolve()


def s3_enabled() -> bool:
    return bool(os.getenv("AWS_S3_BUCKET", "").strip())


def _s3_client():
    """Use explicit keys if set; otherwise EC2 IAM instance profile (recommended)."""
    import boto3

    region = os.getenv("AWS_REGION") or None
    key = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    secret = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
    if key and secret:
        return boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=key,
            aws_secret_access_key=secret,
        )
    return boto3.client("s3", region_name=region)


def _local_path(key: str) -> Path:
    p = _local_root() / key.replace("\\", "/").lstrip("/")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> dict:
    key = key.replace("\\", "/").lstrip("/")
    if s3_enabled():
        try:
            client = _s3_client()
            bucket = os.environ["AWS_S3_BUCKET"]
            client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
            return {"backend": "s3", "key": key, "bucket": bucket, "size": len(data)}
        except ImportError:
            pass
        except Exception as e:
            return {"error": f"S3 upload failed: {e}"}
    path = _local_path(key)
    path.write_bytes(data)
    return {"backend": "local", "key": key, "path": str(path), "size": len(data)}


def get_bytes(key: str) -> Optional[bytes]:
    key = key.replace("\\", "/").lstrip("/")
    if s3_enabled():
        try:
            bucket = os.environ["AWS_S3_BUCKET"]
            obj = _s3_client().get_object(Bucket=bucket, Key=key)
            return obj["Body"].read()
        except Exception:
            pass
    path = _local_path(key)
    if path.is_file():
        return path.read_bytes()
    return None


def delete_object(key: str) -> bool:
    key = key.replace("\\", "/").lstrip("/")
    ok = False
    if s3_enabled():
        try:
            _s3_client().delete_object(Bucket=os.environ["AWS_S3_BUCKET"], Key=key)
            ok = True
        except Exception:
            pass
    path = _local_path(key)
    if path.is_file():
        path.unlink(missing_ok=True)
        ok = True
    return ok
