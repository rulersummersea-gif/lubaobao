#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/lubaobao}"
REPO_URL="${REPO_URL:-https://github.com/rulersummersea-gif/lubaobao.git}"
BRANCH="${BRANCH:-main}"

echo "[1/6] Preparing system packages..."
if ! command -v git >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y git
fi

if ! command -v docker >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl gnupg
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

echo "[2/6] Syncing repository..."
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
else
  sudo mkdir -p "$APP_DIR"
  sudo chown "$USER:$USER" "$APP_DIR"
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

echo "[3/6] Creating data directories..."
sudo mkdir -p /opt/lubaobao-data/uploads
sudo chown -R "$USER:$USER" /opt/lubaobao-data

echo "[4/6] Starting backend..."
cd "$APP_DIR/backend"
docker compose down || true
if docker ps -a --format '{{.Names}}' | grep -qx 'lubaobao-api'; then
  docker stop lubaobao-api || true
  docker rm lubaobao-api || true
fi
docker compose up -d --build

echo "[5/6] Waiting for API..."
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:18080/health >/dev/null; then
    break
  fi
  sleep 2
done

echo "[6/6] Smoke testing endpoints..."
curl -fsS http://127.0.0.1:18080/health
echo
curl -fsS http://127.0.0.1:18080/
echo
curl -fsS http://127.0.0.1:18080/material-packs?enterpriseId=1
echo

echo "Deploy complete: http://$(curl -fsS ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}'):18080"
