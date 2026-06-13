---
name: webar-mindar-ios
description: >-
  Build, debug, and ship browser-based AR image-tracking experiences (MindAR +
  A-Frame + Three.js inside a Next.js App Router H5), and especially diagnose the
  iOS-Safari/WebKit-only failures that desktop Chromium never reproduces — blank
  or black camera after "start AR", scenes collapsing to width:0, next/image not
  rendering, gyro/DeviceOrientation not firing. Use this whenever the task
  involves WebAR / MindAR / A-Frame / image-tracking / "扫描识别" AR on phones, an
  AR page that works in Chrome but is blank/broken on iPhone, reproducing iOS
  WebKit bugs without a physical device, or deploying such an app to a GCE VM
  behind a cloudflare quick tunnel for on-phone testing. Reach for it even when
  the user just says "the camera is blank on iPhone after I tap start" or "make
  the AR camera fullscreen" — the iOS-WebKit gotchas and the Playwright-WebKit
  verification combo here save hours of guess-and-redeploy.
---

# WebAR (MindAR) on Next.js — build, iOS-WebKit debug, and deploy

This skill captures a battle-tested workflow for **web AR image tracking** (point
the phone camera at a printed/displayed target, anchor an animated overlay on it)
built as a **Next.js H5** page, plus the parts that are genuinely hard: **iOS
WebKit-only bugs** and **how to verify them without a physical iPhone**.

The single most important idea: **iOS Safari AND iOS Chrome both run WebKit**
(Apple mandates it). Desktop Chromium ≠ iOS. A page that is perfect in Chromium
can be blank on every iPhone browser. So the verification loop is built around
**Playwright's WebKit engine** (= Safari's engine) on the desktop, with a
**fake camera injected via `getUserMedia` override**, because that's the only way
to see the real error fast instead of round-tripping screenshots with the user.

## Tech stack (what actually shipped)

**AR runtime** (vendored as static files under `public/vendor/ar/`, not npm — keeps
them out of the bundle and lets you cache-bust with a `?v=` query):
- A-Frame `1.5.0` + MindAR `mindar-image-aframe 1.2.5` (image tracking) + Three.js (bundled in A-Frame).
- Targets are precompiled `.mind` files (from the printed artwork) served from `public/`.

**App**: Next.js 16 (App Router) + React 19, AR components are `"use client"`.
- MindAR/A-Frame scripts are **lazy-loaded only after a user gesture** ("开启 AR")
  via a `loadMindArScripts()` that appends `<script>` and resolves on `onload`.
- The AR scene is a reusable `ArImageTrackingScene` component wrapping the
  `<a-scene mindar-image>` + `<a-camera>` + a target `<a-entity mindar-image-target>`.
- Visual approach is **2.5D parallax + CSS/SVG/Canvas placeholders + render
  tiering** (`full | lite | 2d`), NOT real 3D models — cheapest, most WebView-compatible.

**Verification**: Playwright **WebKit** (desktop Safari engine) + fake camera,
plus jsdom unit tests (vitest) that mock MindAR/getUserMedia. The two are
complementary — see "Why the test pyramid has a hole" below.

**Deploy (for on-phone testing / staging)**: source tarball → GCE VM over IAP SSH
→ `npm ci && next build && next start` (Node 20 via nvm) → **cloudflare quick
tunnel** for an instant public HTTPS URL. (Real production for a China 文旅/微信
audience is a *separate* target — Aliyun + ICP 备案 + `.cn`; GCP is blocked/slow in
mainland China and only suitable for staging.)

## The verification combo (read this first — it is the point of the skill)

When an AR page is "blank/broken on iPhone but fine in Chrome", do NOT keep asking
the user to retry. Reproduce it yourself in WebKit. Full scripts and the exact
flow are in **`references/verification-playwright-webkit.md`** and
**`scripts/webkit-repro.mjs`**. The essentials:

1. **Use the WebKit engine, emulating an iPhone.** `npx playwright install webkit`
   (it must match your installed `playwright` version), then
   `webkit.launch()` + `browser.newContext({ ...devices['iPhone 13'] })`.
2. **Inject a fake camera** — Playwright WebKit has NO `--use-fake-device...` flag
   (that's Chromium-only) and `grantPermissions(['camera'])` throws ("Unknown
   permission"). Instead, in an `addInitScript`, override
   `navigator.mediaDevices.getUserMedia` to return a `canvas.captureStream()`. Now
   MindAR mounts and proceeds as if a camera exists.
3. **Capture everything**: `page.on('console' | 'pageerror' | 'requestfailed')`.
4. **Drive the real state machine**: click "开启 AR", then **wait long enough**
   for the heavy vendored scripts to download (A-Frame ~1.4MB + MindAR ~1.7MB —
   over a slow tunnel this can be 20s+; too short a wait looks like a hang at the
   loading spinner and sends you chasing the wrong bug).
5. **Measure layout, not just presence**: after the scene mounts, read
   `getBoundingClientRect()` of `a-scene`, `<video>`, `<canvas>`. A WebKit-only
   `width: 0` is the classic blank-camera cause. If width is 0, **walk the DOM
   ancestors logging each `offsetWidth`** to find the element that collapses.

Versions/UA matter: the user's iPhone may run an **older** WebKit than Playwright's
latest. If you cannot reproduce with the latest, ask for their iOS version and
match it, or use the on-screen error overlay (below) to read the real device error.

## iOS-WebKit gotchas catalogue

These are documented with root cause + fix in
**`references/ios-webkit-gotchas.md`**. The headline ones:

- **AR viewport collapses to `width:0` (blank camera after "start AR").** Cause: a
  CSS-grid container with `place-items-center` (i.e. `justify-items: center`) sizes
  its in-flow grid item to *content width*; when the only children are
  absolutely-positioned (`a-scene`, overlays) there is no content width → WebKit
  collapses it to 0 (Chromium happened to keep a width, so it only repros on iOS).
  **Fix: make the AR scene container fill its positioned parent with
  `absolute inset-0` instead of in-flow `relative h-full`** — the same pattern a
  working `next/image fill` already uses.
- **`next/image` blank on some iOS versions.** The optimizer + AVIF/format
  negotiation can yield an image the device can't decode (works via `curl` with a
  PNG `Accept`). For pre-sized art, set `images: { unoptimized: true }` to serve
  the raw file and sidestep the optimizer entirely.
- **Gyro/DeviceOrientation never fires on iOS 13+.** You must call
  `DeviceOrientationEvent.requestPermission()` from inside a user gesture; gate the
  listener on the grant and always keep a touch-drag fallback.
- **Camera "shows then goes black" / not visible.** Keep the `<video>` explicitly
  visible via CSS, and avoid React effect-cleanup tearing down MindAR — store
  callbacks in a `ref` so the effect doesn't re-run and `stop()` the tracker.
- **Fullscreen AR.** A small embedded `aspect-[4/3]` box feels tiny; when the
  camera is active, promote the viewport to `fixed inset-0` (camera fills screen),
  float the controls in a bottom sheet (`fixed bottom-0`, safe-area padded), hide
  page chrome, and add a safe-area-aware exit button.

## Build patterns worth reusing

- **Load AR scripts only on user gesture**, then transition state
  (`entry → loading → scanning → tracking`). Camera permission appears only after
  the tap — required for iOS and good for trust.
- **One reusable `ArImageTrackingScene`** (single target, `targetIndex`, callbacks
  `onSceneReady/onSceneError/onTargetFound/onTargetLost`) keeps every AR page
  consistent and keeps the black-screen mitigation in one place.
- **Render tiering** (`detectRenderTier()` → full/lite/2d from
  `prefers-reduced-motion`, `hardwareConcurrency`, `deviceMemory`, WeChat UA) so
  low-end phones and WeChat WebView degrade instead of breaking.
- **On-screen error overlay**: a tiny client component that listens for
  `window.error`/`unhandledrejection` and renders a dismissible panel only when an
  error occurs. This is your "remote eyes" on a real phone when you can't attach a
  Mac/Safari Web Inspector.
- **Cultural/red-line guards as code**: when content has hard "must not say/show"
  rules, encode them as a copy whitelist that throws + test assertions that scan
  for forbidden strings, so they can't regress.

## Deploy for on-phone testing

Full pipeline + the exact gotchas in **`references/deploy-gce-cloudflare.md`** and
the template in **`scripts/deploy-gce-cloudflare.sh`**. The traps that cost time:

- **IAP SSH is flaky** — wrap every `gcloud compute ssh/scp` in a retry loop, and
  **run the actual deploy as a `setsid` detached script on the VM** that logs to a
  file, then poll the log. A dropped SSH must not kill the build.
- **Next 16 needs Node ≥ 20.9** — install via `nvm` on the VM (don't touch system Node).
- **Private repo + broken `gh` auth on the VM** → ship a **source tarball via scp**
  (exclude `node_modules/.next/.git` and stray junk like a Windows `D:/...` cache
  dir) and `npm ci` on the VM, rather than `git pull`.
- **`next start` renames its process to `next-server`** — `pkill -f "next start"`
  misses it, so the old build keeps port 3100 and your new build silently fails to
  bind. **Kill by port** (`ss -tlnp` → pid → `kill -9`).
- **Keep a stable tunnel URL across redeploys** by restarting only `next`, not
  `cloudflared` (the quick-tunnel URL changes every time cloudflared restarts).
- Cache-bust client retests with a `?v=N` query (Safari caches aggressively; even
  "private tab" can mislead if you don't change the URL).

## When to stop and hand off

You can verify everything *except* a real camera recognizing a real printed target
and device-specific performance/heat. That last mile (recognition rate across a
device matrix, WeChat WebView, real lighting) is the human's on-site job — say so
plainly rather than implying you tested it.
