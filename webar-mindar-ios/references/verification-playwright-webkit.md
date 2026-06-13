# Verifying WebAR on iOS WebKit without a physical iPhone

The hard problem: an AR page is blank/broken on the user's iPhone but perfect in
your desktop Chrome, and round-tripping screenshots with the user is slow and
lossy. The solution: **reproduce in WebKit yourself.**

## The test pyramid has a hole — fill it with WebKit

- **jsdom unit tests (vitest)** mock `getUserMedia`, A-Frame/MindAR `<script>`
  loads, and dispatch synthetic `targetFound/targetLost`. They verify the *state
  machine* and DOM wiring, and they're fast and deterministic. **But they cannot
  see layout, real WebGL, camera painting, or WebKit-specific CSS.** A page can be
  246/246 green in jsdom and still be a blank `width:0` box on a real iPhone.
- **Desktop Chromium (e.g. agent-browser)** runs the real browser, real CSS, real
  hydration — great for catching universal JS/render bugs, but it is NOT WebKit, so
  it misses every iOS-only bug (which is exactly the class you're chasing).
- **Playwright WebKit = Safari's engine.** This is the layer that actually
  reproduces iOS-only failures on the desktop. Make it the centerpiece.

## Setup

```bash
mkdir -p /tmp/wktest && cd /tmp/wktest
npm init -y
npm i playwright
npx playwright install webkit   # must match the installed playwright version;
                                # a version mismatch errors with the needed revision
```

Notes:
- Playwright bundles its own WebKit build (e.g. "WebKit 26.x"); it tracks roughly
  current Safari, which may be **newer** than the user's iPhone. If you can't
  reproduce, ask for their iOS version and match it (older Playwright → older
  WebKit), or fall back to the on-screen error overlay on the real device.
- There is a **separate** Python `playwright` shim on many machines that may be
  broken/unrelated — use the Node package you just installed.

## The fake-camera trick (WebKit has no fake-camera flag)

Chromium has `--use-fake-device-for-media-stream` + `--use-file-for-fake-video-capture`.
**WebKit has neither**, and Playwright `context.grantPermissions(['camera'])`
throws `Unknown permission: camera`. So inject a synthetic stream before page
scripts run:

```js
await context.addInitScript(() => {
  const c = document.createElement('canvas'); c.width = 640; c.height = 480;
  const g = c.getContext('2d');
  (function draw(){ g.fillStyle='#1d3b53'; g.fillRect(0,0,640,480);
    g.fillStyle='#e8cc7e'; g.fillRect(Math.random()*560,Math.random()*400,60,60);
    requestAnimationFrame(draw); })();
  const stream = c.captureStream(15);
  if (navigator.mediaDevices) {
    navigator.mediaDevices.getUserMedia = async () => stream;
    navigator.mediaDevices.enumerateDevices = async () =>
      [{ kind:'videoinput', deviceId:'fake', label:'fake', groupId:'g' }];
  }
});
```

Now MindAR's `getUserMedia` "succeeds", the `<a-scene>` mounts, and you observe the
real scanning/rendering path — including whether it paints or collapses.

## The flow that actually finds the bug

1. `webkit.launch()` + `newContext({ ...devices['iPhone 13'] })` (mobile viewport,
   iOS UA, touch). Run both default-viewport and iPhone-emulation if unsure —
   mobile viewport sometimes triggers layout bugs the desktop one doesn't.
2. Capture `console`, `pageerror`, `requestfailed`.
3. `goto(url, { waitUntil: 'load' })`, then click "开启 AR" (via `evaluate` →
   `btn.click()`; an automation `.click()` sometimes doesn't fire the React
   handler, while a real DOM `.click()` does).
4. **Wait long enough** for the vendored scripts (A-Frame ~1.4MB + MindAR ~1.7MB)
   to download — 20–25s over a slow tunnel. Too-short a wait shows a "stuck at
   loading spinner" state and misleads you; it's just still downloading.
5. After mount, **measure layout**: `getBoundingClientRect()` on `a-scene`,
   `<video>`, `<canvas>`. `width: 0` ⇒ the collapse bug (#1 in the gotchas).
6. If collapsed, **walk ancestors** logging each element's rounded `width`,
   `display`, `position`, `justifyItems` — the first element with `width: 0` whose
   parent is non-zero is where to apply the fix.
7. Screenshot for a visual sanity check (`page.screenshot`).

`scripts/webkit-repro.mjs` is a ready-to-run version. Invoke:
`node webkit-repro.mjs <url> [--width-walk]`.

## Confirm a fix before redeploying (saves cycles)

The deploy round-trip is slow and flaky. Before committing+redeploying a CSS fix,
**inject the candidate fix in the live WebKit session and re-measure**:

```js
// e.g. test that absolute-inset-0 un-collapses the scanning container
await page.evaluate(() => {
  const sc = document.querySelector('.jygc-ar-scene')?.parentElement;
  Object.assign(sc.style, { position:'absolute', top:0, left:0, right:0, bottom:0, width:'auto' });
});
// then re-read a-scene width — 0 → 348 confirms the fix
```

Then also verify **locally** against `next start` (production build, not dev) at
`http://localhost:<port>` with the same WebKit script, before paying for a deploy.

## On-device fallback: the on-screen error overlay

When you genuinely can't reproduce (older iOS WebKit) and can't attach Safari Web
Inspector, ship a tiny client component that renders nothing until it catches
`window.error`/`unhandledrejection`, then shows a dismissible red panel with the
message. The user screenshots it → you get the real device error. Keep it always
mounted in the root layout; it's invisible in the happy path.

## Don't forget: cache + reproduction hygiene

- Safari caches hard. Cache-bust retests with `?v=N`; even a "private tab" can show
  stale results if the URL is identical. Confirm the user is on the new build (the
  on-screen overlay or a visible build marker is the unambiguous signal).
- A repro that "works" in your latest WebKit doesn't clear the user's older iOS —
  state that limitation explicitly and get their iOS version when stuck.
