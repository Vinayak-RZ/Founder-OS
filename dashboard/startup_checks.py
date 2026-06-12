"""Warn on insecure or incomplete production configuration at boot."""
from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)
_PIN_RE = re.compile(r"^\d{6}$")


def run_startup_checks() -> None:
    from config import config

    if not config.public_base_url:
        return

    if not config.dashboard_pin or not _PIN_RE.match(config.dashboard_pin):
        logger.warning(
            "PRODUCTION: PUBLIC_BASE_URL is set but DASHBOARD_PIN is missing or not 6 digits — "
            "the UI is exposed without a PIN gate."
        )
    if not config.behind_proxy:
        logger.warning(
            "PRODUCTION: set BEHIND_PROXY=true when TLS terminates at Cloudflare/nginx."
        )
    if not config.flask_secret_key or config.flask_secret_key == "dev-change-me":
        logger.warning(
            "PRODUCTION: set a strong FLASK_SECRET_KEY for session security."
        )
    if not os.getenv("AWS_S3_BUCKET", "").strip():
        logger.warning(
            "PRODUCTION: AWS_S3_BUCKET not set — vault files will use local disk only."
        )
