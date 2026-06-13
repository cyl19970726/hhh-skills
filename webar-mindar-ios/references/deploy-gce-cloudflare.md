# Deploy a Next.js WebAR app to a GCE VM via cloudflare quick tunnel (staging / on-phone testing)

Goal: get the AR page onto a **public HTTPS URL** fast so the user can open it on a
real phone (AR/camera needs a secure context). This is **staging**, not production.

> **Production vs staging — be explicit.** GCP/GCE is fine for staging but is
> blocked/throttled in mainland China; a China 文旅/微信 audience needs a separate
> production target (Aliyun + ICP 备案 + a `.cn` domain). Don't let a working GCE
> staging URL imply production-readiness for that audience.

## Pipeline overview

1. Push the branch (so it exists remotely) — or skip if shipping a tarball.
2. Tarball the source → `scp` to the VM (avoids needing git creds on the VM).
3. On the VM: Node 20 via nvm → extract → `npm ci` → `next build` → `next start -p 3100`.
4. `cloudflared tunnel --url http://localhost:3100` → public `*.trycloudflare.com` URL.
5. Verify with `curl` + a WebKit repro against the public URL.

`scripts/deploy-gce-cloudflare.sh` is a parameterized template. The traps below are
what actually cost hours — internalize them.

## Trap 1: IAP SSH/SCP is flaky → retry + detach

`gcloud compute ssh ... --tunnel-through-iap` intermittently dies mid-connection
(`SSL: UNEXPECTED_EOF`, `ProxyError`, websocket `ConnectionCreationError`). Two
rules:

- **Wrap every ssh/scp in a retry loop** (success is intermittent; ~8–12 tries).
- **Never run a long build inside the SSH session.** Push a script to the VM and
  run it **detached** so a dropped SSH doesn't kill it, then poll its log:
  ```bash
  # launch (note: NO pkill that matches the launcher's own command line)
  gcloud compute ssh VM --zone Z --tunnel-through-iap --command \
    'chmod +x $HOME/deploy.sh; setsid bash $HOME/deploy.sh </dev/null >$HOME/deploy.log 2>&1 & echo LAUNCHED'
  # then poll:
  gcloud compute ssh VM --zone Z --tunnel-through-iap --command 'tail -6 $HOME/deploy.log'
  ```
- **Beware self-suicide:** a launch command containing `pkill -f deploy.sh` will
  match and kill the very shell running it (its args contain `deploy.sh`) before it
  echoes success. Don't `pkill` the script name in the launcher; let the script do
  targeted kills internally.
- If the sandbox proxy is the culprit, run the gcloud commands with the sandbox
  disabled. Transferring a script as base64 inline can exceed arg limits / break
  quoting — prefer `gcloud compute scp` for files.

## Trap 2: Node version

Next 16 requires Node ≥ 20.9; a VM may have 18. Install via **nvm** (don't touch
the system Node — other services may depend on it):
```bash
[ -s ~/.nvm/nvm.sh ] || curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
. ~/.nvm/nvm.sh; nvm install 20 >/dev/null; nvm use 20
```

## Trap 3: getting the code onto the VM

Private repo + the VM's `gh`/git creds may be **expired** (`gh auth status` fails).
Don't assume `git pull` works. Most robust: **ship a source tarball**:
```bash
tar czf /tmp/src.tgz \
  --exclude='./node_modules' --exclude='*/node_modules' \
  --exclude='./.next' --exclude='./.git' --exclude='./.cache' \
  --exclude='./D:' --exclude='./.local' --exclude='./tmp' --exclude='./.vercel' .
```
- **Exclude junk aggressively.** A repo can hide a huge stray cache (e.g. a
  Windows-path dir `./D:/.../.cache/npm` ballooned a tarball to 193MB → 19MB after
  excluding). Check `du -sh` of top dirs / largest files if the tarball is big.
- `npm ci` **on the VM** (don't ship `node_modules` — native deps like Next's SWC
  are platform-specific; macOS binaries won't run on Linux).

## Trap 4: `next start` process name → kill by PORT, not name

After startup, Next renames its process to **`next-server`**. So
`pkill -f "next start -p 3100"` does NOT match the running server → the old build
keeps port 3100 → your freshly-built server fails to bind and you keep serving the
**old** build (very confusing: "my fix didn't take effect"). Kill by port:
```bash
PIDS=$(ss -tlnp 2>/dev/null | grep ':3100 ' | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u)
[ -n "$PIDS" ] && kill -9 $PIDS
pkill -9 -f next-server 2>/dev/null || true
```
Also `rm -rf .next` before rebuild if you suspect a stale build is being served,
and **verify the served HTML** (`curl` the URL, grep for the change) before
concluding a fix is live.

## Trap 5: cloudflare quick tunnel URL is ephemeral

`cloudflared tunnel --url http://localhost:3100` prints a random
`https://<words>.trycloudflare.com` that **changes every time cloudflared
restarts** and dies when the VM reboots or the process is killed. So:
- On a **redeploy**, restart only `next` (kill by port + relaunch) and **leave
  cloudflared running** → the URL stays stable for the user.
- The detached processes do **not** survive a VM reboot — for durable staging set
  up a `systemd` unit (next) + a cloudflare **named** tunnel (needs a CF account).
- Install cloudflared if absent: download the static
  `cloudflared-linux-amd64` release binary to `~/bin` and `chmod +x`.

## Verify the deploy

```bash
curl -s -o /dev/null -w "%{http_code}\n" "$URL/ar/<slug>"          # page 200
curl -s "$URL/ar/<slug>" | grep -oE '/_next/image|/your-asset.png' # confirm the build (e.g. unoptimized img)
# vendored AR + .mind targets reachable:
curl -s -o /dev/null -w "%{http_code}\n" "$URL/vendor/ar/mindar-image-aframe-1.2.5.prod.js"
curl -s -o /dev/null -w "%{http_code}\n" "$URL/ar/<slug>/targets/<target>.mind"
```
Then run `scripts/webkit-repro.mjs $URL/ar/<slug>` to confirm the AR scene renders
(not `width:0`) in WebKit before handing the URL to the user. Note: large assets
over the tunnel sometimes return curl `000` (transient connection reset) — retry a
couple times before believing a 404.
