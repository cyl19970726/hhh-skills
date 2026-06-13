#!/usr/bin/env bash
# Template: deploy a Next.js (Node 20) app to a GCE VM and expose it via a
# cloudflare quick tunnel for on-phone testing. Runs ON the VM, detached.
# Copy/scp this to the VM and launch with:
#   setsid bash $HOME/deploy.sh </dev/null >$HOME/deploy.log 2>&1 &
# Ship the source as a tarball (~/jy-src.tgz) first (see references/deploy-gce-cloudflare.md).
#
# Edit DIR / PORT / ROUTE for your app.
set -uo pipefail
echo "===== DEPLOY START $(date -u) ====="

DIR="$HOME/app-deploy"
TGZ="$HOME/app-src.tgz"
PORT=3100
ROUTE="/ar/chenghuangmiao"          # a route to health-check
KEEP_TUNNEL="${KEEP_TUNNEL:-0}"     # 1 = restart only next, keep existing cloudflared (stable URL)

[ -f "$TGZ" ] || { echo "FATAL: $TGZ missing"; echo "===== DEPLOY FAIL ====="; exit 2; }

# --- Node 20 via nvm (do not touch system node) ---
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] || curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash >/dev/null 2>&1
. "$NVM_DIR/nvm.sh"; nvm install 20 >/dev/null 2>&1; nvm use 20 >/dev/null 2>&1
echo "node: $(node -v)"

# --- extract source (clean) + install + build ---
rm -rf "$DIR"; mkdir -p "$DIR"
tar xzf "$TGZ" -C "$DIR" || { echo "FATAL extract"; echo "===== DEPLOY FAIL ====="; exit 3; }
cd "$DIR" || exit 4
npm ci >/tmp/deploy-npm.log 2>&1 || { echo "FATAL npm ci"; tail -20 /tmp/deploy-npm.log; echo "===== DEPLOY FAIL ====="; exit 5; }
rm -rf .next
npm run build >/tmp/deploy-build.log 2>&1 || { echo "FATAL build"; tail -25 /tmp/deploy-build.log; echo "===== DEPLOY FAIL ====="; exit 6; }
echo "build OK"

# --- (re)start next: kill by PORT, because the running process is named `next-server` ---
PIDS=$(ss -tlnp 2>/dev/null | grep -E ":$PORT " | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u)
[ -n "$PIDS" ] && kill -9 $PIDS 2>/dev/null || true
pkill -9 -f next-server 2>/dev/null || true
sleep 2
echo "listeners on $PORT after kill: $(ss -tln 2>/dev/null | grep -c ":$PORT ")"
setsid nohup node "$DIR/node_modules/next/dist/bin/next" start -p "$PORT" >"$HOME/next.log" 2>&1 </dev/null &
for i in $(seq 1 30); do curl -fsS "http://localhost:$PORT$ROUTE" >/dev/null 2>&1 && { echo "SERVING :$PORT"; break; }; sleep 2; done

# --- cloudflare quick tunnel ---
mkdir -p "$HOME/bin"
if ! command -v cloudflared >/dev/null 2>&1 && [ ! -x "$HOME/bin/cloudflared" ]; then
  curl -fsSL -o "$HOME/bin/cloudflared" https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 && chmod +x "$HOME/bin/cloudflared"
fi
CF="$(command -v cloudflared || echo "$HOME/bin/cloudflared")"
if [ "$KEEP_TUNNEL" = "1" ] && pgrep -f "cloudflared tunnel --url http://localhost:$PORT" >/dev/null; then
  echo "keeping existing tunnel (stable URL)"
else
  pkill -f "cloudflared tunnel --url http://localhost:$PORT" 2>/dev/null || true; sleep 1
  setsid nohup "$CF" tunnel --url "http://localhost:$PORT" >"$HOME/tunnel.log" 2>&1 </dev/null &
fi
URL=""
for i in $(seq 1 40); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$HOME/tunnel.log" 2>/dev/null | head -1)
  [ -n "$URL" ] && break; sleep 2
done
[ -n "$URL" ] && echo "PUBLIC_URL=$URL$ROUTE" || { echo "no tunnel URL"; tail -15 "$HOME/tunnel.log"; }
echo "===== DEPLOY DONE $(date -u) ====="
