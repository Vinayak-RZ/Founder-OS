#!/usr/bin/env bash
# Pull latest code and restart Founder OS on EC2.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/founder-os}"

cd "$APP_DIR"
git pull --ff-only
"$APP_DIR/.venv/bin/pip" install -r requirements.txt -q
systemctl restart founder-os
echo "Updated and restarted founder-os."
curl -sf http://127.0.0.1:8787/api/health && echo " — health OK"
