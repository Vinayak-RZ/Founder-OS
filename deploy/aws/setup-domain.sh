#!/usr/bin/env bash
# Configure Founder OS for a custom domain (nginx + env + Let's Encrypt).
# Usage: sudo bash deploy/aws/setup-domain.sh nawab-os.stamped.work
set -euo pipefail

DOMAIN="${1:?Usage: setup-domain.sh your.domain.com}"
ENV_FILE="/etc/founder-os/env"
NGINX_SITE="/etc/nginx/sites-available/founder-os"
BASE_URL="https://${DOMAIN}"

echo "==> Domain: $DOMAIN"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — run bootstrap.sh first."
  exit 1
fi

echo "==> nginx server_name..."
sed -i "s/server_name .*/server_name ${DOMAIN};/" "$NGINX_SITE"
nginx -t
systemctl reload nginx

echo "==> env: PUBLIC_BASE_URL, BEHIND_PROXY, GITHUB_REDIRECT_URI..."
if grep -q '^PUBLIC_BASE_URL=' "$ENV_FILE"; then
  sed -i "s|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=${BASE_URL}|" "$ENV_FILE"
else
  echo "PUBLIC_BASE_URL=${BASE_URL}" >> "$ENV_FILE"
fi
if grep -q '^BEHIND_PROXY=' "$ENV_FILE"; then
  sed -i 's|^BEHIND_PROXY=.*|BEHIND_PROXY=true|' "$ENV_FILE"
else
  echo 'BEHIND_PROXY=true' >> "$ENV_FILE"
fi
if grep -q '^GITHUB_REDIRECT_URI=' "$ENV_FILE"; then
  sed -i "s|^GITHUB_REDIRECT_URI=.*|GITHUB_REDIRECT_URI=${BASE_URL}/api/github/callback|" "$ENV_FILE"
else
  echo "GITHUB_REDIRECT_URI=${BASE_URL}/api/github/callback" >> "$ENV_FILE"
fi

echo "==> certbot (Let's Encrypt)..."
apt-get install -y -qq certbot python3-certbot-nginx
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
  --register-unsafely-without-email --redirect

echo "==> restart founder-os..."
systemctl restart founder-os
sleep 4

echo "==> verify..."
curl -sf "http://127.0.0.1:8787/api/health" && echo " — gunicorn OK"
curl -sfk "https://127.0.0.1/api/health" -H "Host: ${DOMAIN}" && echo " — nginx HTTPS OK"

echo ""
echo "Done. Open ${BASE_URL} and enter your PIN."
echo "Cloudflare: A record -> Elastic IP, SSL/TLS = Full (strict), SG allows 443."
