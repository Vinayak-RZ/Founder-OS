# CI/CD — GitHub Actions → EC2

Pushes to `main` run tests, then SSH to your EC2 instance and execute `deploy/aws/update.sh` (git pull, pip install, restart, health check).

## Architecture

```
git push main
    │
    ▼
GitHub Actions (ci-cd.yml)
    ├── job: test (pytest)
    └── job: deploy (SSH → EC2)
              └── sudo bash /opt/founder-os/deploy/aws/update.sh
```

## One-time EC2 prep

The instance must already have Founder OS bootstrapped at `/opt/founder-os` (see [README.md](README.md)).

Confirm manual update works:

```bash
ssh -i your-key.pem ubuntu@YOUR_ELASTIC_IP
sudo bash /opt/founder-os/deploy/aws/update.sh
```

Ensure `ubuntu` can run deploy without a password prompt:

```bash
sudo -n true && echo OK
```

## GitHub secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|--------|--------|
| `EC2_HOST` | Elastic IP, e.g. `15.135.253.12` |
| `EC2_SSH_PRIVATE_KEY` | Full contents of your `.pem` file (including `BEGIN`/`END` lines) |
| `PRODUCTION_URL` | Public URL, e.g. `https://nawab-os.stamped.work` |

## GitHub environment (recommended)

**Settings → Environments → New environment → `production`**

Optional: require manual approval before deploy, or restrict to `main` branch.

The workflow uses `environment: production` on the deploy job.

## What runs on deploy

1. `git fetch` + `git reset --hard origin/main` as user `founder` (overwrites any local edits on the server)
2. `pip install -r requirements.txt` in `/opt/founder-os/.venv`
3. `systemctl restart founder-os`
4. Poll `http://127.0.0.1:8787/api/health` until OK (or fail the workflow)

## Manual deploy

```bash
ssh ubuntu@YOUR_ELASTIC_IP
sudo bash /opt/founder-os/deploy/aws/update.sh
```

## Security notes

- Prefer a **dedicated deploy SSH key** (not your personal admin key): add its public half to `~ubuntu/.ssh/authorized_keys` on EC2, store the private key only in `EC2_SSH_PRIVATE_KEY`.
- Never commit `.pem` files — they are in `.gitignore`.
- Deploy only runs after **tests pass** on the same commit.
- `concurrency` cancels overlapping deploys so two pushes do not fight on the server.

## Troubleshooting

| Failure | Fix |
|---------|-----|
| `git pull` permission denied | `sudo chown -R founder:founder /opt/founder-os` |
| `Host key verification failed` | Workflow runs `ssh-keyscan`; re-run job |
| Health check timeout | `sudo journalctl -u founder-os -n 50` on EC2 |
| Tests pass locally, fail in CI | Check env placeholders in workflow; optional deps |
