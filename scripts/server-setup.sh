#!/usr/bin/env bash
# PRISM — AWS EC2 Ubuntu 24.04 initial server setup
# Run once as ubuntu user after provisioning the instance.
#
# Prerequisites:
#   - Ubuntu 24.04 LTS EC2 instance (t3.medium or larger recommended)
#   - Security group: inbound 22 (SSH), 80 (HTTP), 443 (HTTPS)
#   - This script should be run as: bash scripts/server-setup.sh
set -euo pipefail

REPO_URL="https://github.com/Jerry-Investment/prism.git"
APP_DIR="/opt/prism"
GH_TOKEN="${GH_TOKEN:-}"   # set in env if repo is private

echo "=== PRISM Server Setup ==="
echo "Target: $APP_DIR"
echo ""

# ─── System packages ──────────────────────────────────────────────────────────
sudo apt-get update -q
sudo apt-get install -y -q \
    git curl ca-certificates gnupg lsb-release \
    htop ufw fail2ban unattended-upgrades

# ─── Docker ───────────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -q
    sudo apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo usermod -aG docker ubuntu
    echo "Docker installed."
else
    echo "Docker already installed: $(docker --version)"
fi

# ─── Clone or update repo ─────────────────────────────────────────────────────
if [[ -d "$APP_DIR/.git" ]]; then
    echo "Repo already exists — pulling latest main..."
    cd "$APP_DIR"
    git fetch origin main
    git reset --hard origin/main
else
    echo "Cloning PRISM repo..."
    sudo mkdir -p "$APP_DIR"
    sudo chown ubuntu:ubuntu "$APP_DIR"
    if [[ -n "$GH_TOKEN" ]]; then
        git clone "https://x-access-token:${GH_TOKEN}@github.com/Jerry-Investment/prism.git" "$APP_DIR"
    else
        git clone "$REPO_URL" "$APP_DIR"
    fi
    cd "$APP_DIR"
fi

# ─── Environment file ─────────────────────────────────────────────────────────
if [[ ! -f "$APP_DIR/.env" ]]; then
    cp "$APP_DIR/.env.production.example" "$APP_DIR/.env"
    echo ""
    echo "⚠️  Created .env from template. Fill in the values before starting:"
    echo "   nano $APP_DIR/.env"
    echo ""
else
    echo ".env already exists — skipping."
fi

# ─── Firewall ─────────────────────────────────────────────────────────────────
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
echo "Firewall configured (SSH + HTTP + HTTPS)."

# ─── Fail2ban ─────────────────────────────────────────────────────────────────
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# ─── Systemd service (optional — starts compose on boot) ──────────────────────
sudo tee /etc/systemd/system/prism.service > /dev/null << 'EOF'
[Unit]
Description=PRISM Backtesting Platform
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/prism
EnvironmentFile=/opt/prism/.env
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
TimeoutStartSec=300
User=ubuntu
Group=docker

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable prism.service
echo "Systemd service 'prism' registered (starts on boot)."

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Fill in /opt/prism/.env (DOMAIN, passwords, etc.)"
echo "  2. Add EC2 public IP / domain to DNS"
echo "  3. Start: cd /opt/prism && docker compose -f docker-compose.prod.yml up -d"
echo "  4. Logs:  docker compose -f docker-compose.prod.yml logs -f"
echo ""
echo "GitHub Secrets to configure (in repo Settings → Secrets):"
echo "  EC2_HOST_STAGING  — staging EC2 public IP or hostname"
echo "  EC2_HOST_PROD     — production EC2 public IP or hostname"
echo "  EC2_SSH_KEY       — private key (cat ~/.ssh/id_ed25519)"
echo "  DOMAIN_STAGING    — e.g. staging.prism.yourdomain.com"
echo "  DOMAIN_PROD       — e.g. prism.yourdomain.com"
