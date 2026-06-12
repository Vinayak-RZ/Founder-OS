# Cloudflare DNS for Founder OS on EC2

Use your existing Cloudflare domain to point at the EC2 instance running Founder OS.

## 1. Elastic IP on AWS

In EC2 → Elastic IPs → Allocate → Associate with your Founder OS instance.

Note the IP (e.g. `3.15.42.100`).

## 2. DNS record in Cloudflare

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select your domain
3. **DNS** → **Records** → **Add record**

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| `A` | `founder` (or `@` for root) | Your Elastic IP | Proxied (orange cloud) |

Example: `founder.yourdomain.com` → EC2.

TTL: Auto.

## 3. SSL/TLS mode

**SSL/TLS** → Overview:

- Recommended: **Full (strict)** — browser ↔ Cloudflare ↔ your server all encrypted.
- On the EC2 instance, install a certificate on nginx:
  - **Option A:** `certbot --nginx -d founder.yourdomain.com` (Let's Encrypt)
  - **Option B:** Cloudflare **Origin Certificate** (SSL/TLS → Origin Server → Create) — install on nginx, 15-year validity

Avoid **Flexible** only (encrypts browser→Cloudflare but not Cloudflare→EC2).

## 4. Founder OS env

In `/etc/founder-os/env`:

```env
PUBLIC_BASE_URL=https://founder.yourdomain.com
BEHIND_PROXY=true
DASHBOARD_PIN=123456
FLASK_SECRET_KEY=generate-a-long-random-string-here
GITHUB_REDIRECT_URI=https://founder.yourdomain.com/api/github/callback
```

Generate secret:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Restart: `sudo systemctl restart founder-os`

## 5. nginx `server_name`

Edit `/etc/nginx/sites-available/founder-os`:

```nginx
server_name founder.yourdomain.com;
```

Reload nginx after certbot or origin cert install.

## 6. PIN access

Visitors open `https://founder.yourdomain.com` → 6-digit PIN screen → full Founder OS.

The PIN is set only in server env (`DASHBOARD_PIN`), not in Cloudflare.

## 7. Optional Cloudflare hardening

| Feature | Setting |
|---------|---------|
| **WAF** | Free tier basic rules |
| **Access** | Optional extra layer (Cloudflare Zero Trust) — not required if PIN is enough |
| **Bot Fight Mode** | Security → Bots — can help reduce noise |

## 8. Verify

```bash
curl -sI https://founder.yourdomain.com | head -5
curl -s https://founder.yourdomain.com/api/auth/status
# {"authenticated":false,"pin_required":true,...}
```

Open the URL on phone/laptop → enter PIN → Control center loads.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| 522 / connection timed out | Security group allows 80/443 from `0.0.0.0/0`; nginx running |
| Redirect loop | Set SSL mode to **Full (strict)** and valid cert on origin |
| PIN works locally but not via domain | Set `BEHIND_PROXY=true` and `SESSION_COOKIE_SECURE` (automatic when `BEHIND_PROXY=true`) |
| GitHub OAuth fails | Callback URL in GitHub app must match `GITHUB_REDIRECT_URI` exactly |
