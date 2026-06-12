"""Tests for infrastructure health probes."""
from __future__ import annotations

from unittest.mock import patch

import integrations.infrastructure_health as ih


def test_ec2_host_local_when_no_metadata():
    with patch.object(ih, "_imds_token", return_value=None):
        host = ih._ec2_host()
    assert host["platform"] == "local"
    assert host["ok"] is True


def test_ec2_host_reads_metadata():
    with patch.object(ih, "_imds_token", return_value="tok"):
        with patch.object(ih, "_imds_get", side_effect=lambda path, _t: {
            "instance-id": "i-abc123",
            "placement/region": "ap-southeast-2",
            "instance-type": "t3.small",
            "placement/availability-zone": "ap-southeast-2a",
            "iam/security-credentials/": "FounderOSVaultRole\n",
        }.get(path)):
            host = ih._ec2_host()
    assert host["platform"] == "ec2"
    assert host["instance_id"] == "i-abc123"
    assert host["region"] == "ap-southeast-2"
    assert host["iam_role"] == "FounderOSVaultRole"


def test_s3_status_not_configured(monkeypatch):
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    out = ih._s3_status()
    assert out["configured"] is False
    assert out["ok"] is False


def test_collect_overall_ok_local(monkeypatch):
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    with patch.object(ih, "_ec2_host", return_value={"platform": "local", "ok": True}):
        with patch.object(ih, "_disk_usage", return_value={"ok": True, "free_gb": 10, "total_gb": 50}):
            data = ih.collect(probe_s3_write=False)
    assert data["ok"] is True
    assert data["app"]["storage_backend"] == "local"
    assert "checked_at" in data
