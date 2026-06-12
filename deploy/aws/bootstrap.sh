#!/usr/bin/env bash
# Founder OS — first-time EC2 setup (Ubuntu 22.04+). Run as root or with sudo.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/founder-os}"
APP_USER="${APP_USER:-founder}"
DATA_DIR="${DATA_DIR:-/var/lib/founder-os/data}"
ENV_FILE="/etc/founder-os/env"

echo "==> Installing system packages..."
apt-get update -qq
apt-get install -y --no-install-recommends \
  python3 python3-venv python3-pip git nginx curl ca-certificates

if ! id "$APP_USER" &>/dev/null; then
  useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi

if [[ ! -d "$APP_DIR/.git" ]]; then
  echo "Clone the repo to $APP_DIR first, then re-run bootstrap."
  exit 1
fi

echo "==> Python venv + dependencies..."
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "==> Data directories..."
mkdir -p "$DATA_DIR" /etc/founder-os /var/log/founder-os
chown -R "$APP_USER:$APP_USER" "$DATA_DIR" /var/log/founder-os
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$APP_DIR/deploy/aws/env.production.example" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "Created $ENV_FILE — edit before starting the service."
fi

echo "==> systemd unit..."
cp "$APP_DIR/deploy/aws/founder-os.service" /etc/systemd/system/founder-os.service
systemctl daemon-reload

echo ""
echo "Bootstrap complete."
echo "  1. Edit $ENV_FILE"
echo "  2. Configure nginx: deploy/aws/nginx-founder-os.conf"
echo "  3. systemctl enable --now founder-os"
