# Founder OS on AWS (EC2 + S3 + Qdrant Cloud)

Single-user production layout:

| Layer | Service | Role |
|-------|---------|------|
| **Compute** | EC2 (`t3.small` or larger) | Web UI, agent loop, scheduler |
| **Object storage** | S3 | Vault document payloads, large files |
| **Vectors** | Qdrant Cloud | Semantic memory + catalog search |
| **App state** | EBS volume on EC2 | SQLite DB, OAuth tokens, logs |

You do **not** need RDS or ElastiCache for a personal deployment. SQLite on a persistent EBS volume is sufficient for one operator.

## Architecture

```
Browser (any device)
       │
       ▼
  nginx :443 (TLS)
       │
       ▼
  Gunicorn → Flask :8787 (127.0.0.1 only)
       │
       ├── SQLite (EBS: /var/lib/founder-os/data)
       ├── S3 bucket (vault files via IAM role)
       └── Qdrant Cloud (HTTPS)
```

## Prerequisites

1. **AWS account** with permissions to create EC2, S3, IAM roles, security groups.
2. **Qdrant Cloud** cluster — [cloud.qdrant.io](https://cloud.qdrant.io) — URL + API key.
3. **LLM API key** — Groq, Gemini, or OpenAI (at least one).
4. **Domain on Cloudflare** — point an A record at your EC2 Elastic IP. See [`cloudflare.md`](cloudflare.md).
5. **6-digit PIN** — set `DASHBOARD_PIN` in env so only you can open the UI.
6. **GitHub OAuth App** (optional) — callback `https://YOUR_DOMAIN/api/github/callback`.

## 1. Create S3 bucket

```bash
aws s3 mb s3://founder-os-vault-YOURNAME --region us-east-1
aws s3api put-bucket-versioning --bucket founder-os-vault-YOURNAME \
  --versioning-configuration Status=Enabled
```

Enable default encryption (SSE-S3) in the console. Block public access (default).

## 2. IAM role for EC2

Attach an instance profile with S3 access. Use `deploy/aws/iam-s3-policy.json` as an inline policy (replace `BUCKET_NAME`).

```bash
aws iam create-role --role-name FounderOS-EC2-Role \
  --assume-role-policy-document file://deploy/aws/iam-trust-ec2.json

aws iam put-role-policy --role-name FounderOS-EC2-Role \
  --policy-name FounderOS-S3-Vault \
  --policy-document file://deploy/aws/iam-s3-policy.json

aws iam create-instance-profile --instance-profile-name FounderOS-EC2-Profile
aws iam add-role-to-instance-profile \
  --instance-profile-name FounderOS-EC2-Profile \
  --role-name FounderOS-EC2-Role
```

**Do not** put `AWS_ACCESS_KEY_ID` on the instance if you use an IAM role.

## 3. Launch EC2

| Setting | Recommendation |
|---------|----------------|
| AMI | Ubuntu 22.04 LTS |
| Type | `t3.small` (2 vCPU, 2 GB) minimum; `t3.medium` if heavy agent use |
| Storage | 30 GB gp3 EBS (SQLite + logs; vault payloads live in S3) |
| Security group | SSH (22) from **your IP only**; HTTP (80) + HTTPS (443) from your IP or `0.0.0.0/0` if you need mobile access |
| IAM | Attach `FounderOS-EC2-Profile` |

Allocate and associate an **Elastic IP** so the address survives restarts.

## 4. Bootstrap the instance

SSH in, then:

```bash
sudo bash deploy/aws/bootstrap.sh
```

Or clone first:

```bash
git clone https://github.com/YOUR_ORG/Founder-OS.git /opt/founder-os
cd /opt/founder-os
sudo bash deploy/aws/bootstrap.sh
```

## 5. Configure environment

```bash
sudo cp deploy/aws/env.production.example /etc/founder-os/env
sudo nano /etc/founder-os/env
```

Required values:

- `PUBLIC_BASE_URL=https://your-domain.com`
- `QDRANT_URL`, `QDRANT_API_KEY`
- At least one LLM key
- `AWS_S3_BUCKET`, `AWS_REGION`
- `MY_NAME`, `MY_COMPANY_NAME`, etc.

```bash
sudo systemctl enable founder-os
sudo systemctl start founder-os
```

## 6. TLS with nginx + Certbot

```bash
sudo cp deploy/aws/nginx-founder-os.conf /etc/nginx/sites-available/founder-os
# Edit server_name to your domain
sudo ln -sf /etc/nginx/sites-available/founder-os /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

Set in `/etc/founder-os/env`:

```
BEHIND_PROXY=true
GITHUB_REDIRECT_URI=https://your-domain.com/api/github/callback
```

Restart: `sudo systemctl restart founder-os`

## 7. Verify

```bash
curl -s https://your-domain.com/api/health
# {"ok":true,"storage":"s3"}

sudo journalctl -u founder-os -f
```

Open `https://your-domain.com` from any device.

## Updates

**Automatic (recommended):** push to `main` — GitHub Actions runs tests and deploys via SSH. See [DEPLOY.md](DEPLOY.md) for secrets setup.

**Manual:**

```bash
cd /opt/founder-os
sudo bash deploy/aws/update.sh
```

## What else you might need

| Need | When |
|------|------|
| **Elastic IP** | Stable URL for DNS |
| **HTTPS** | GitHub OAuth, secure access from phone/laptop |
| **EBS snapshots** | Weekly backup of SQLite + tokens (in addition to S3 vault) |
| **SSM Parameter Store** | Alternative to `/etc/founder-os/env` for secrets |
| **CloudWatch** | Ship logs from `journalctl` |
| **Second factor / VPN** | If you expose HTTPS to the internet — this is a personal console with full agent access |

Not required for v1: RDS, Redis, Kubernetes, multi-AZ.

## Docker alternative

```bash
docker compose up -d --build
```

Mount `./data` and set the same env vars. For production on EC2, **systemd + Gunicorn** (this guide) is simpler and uses less RAM than Docker on a small instance.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `storage: local` in `/api/health` | Set `AWS_S3_BUCKET` and attach IAM role |
| GitHub OAuth fails | `GITHUB_REDIRECT_URI` must match OAuth app exactly; use HTTPS |
| 502 from nginx | `systemctl status founder-os`; check Gunicorn on `127.0.0.1:8787` |
| Qdrant errors | Verify URL/key; security group allows outbound HTTPS |
