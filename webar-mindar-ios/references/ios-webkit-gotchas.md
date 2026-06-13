# iOS WebKit gotchas for WebAR (root cause + fix)

iOS Safari **and** iOS Chrome both run WebKit. If something is blank/broken on
"iPhone" but fine in desktop Chrome, it is almost always one of these. Each entry
is a real bug hit while shipping a MindAR AR page and the fix that resolved it.

---

## 1. AR scene collapses to `width: 0` → blank camera after tapping "start AR"

**Symptom:** Entry page is fine. After "开启 AR" + camera permission, the camera
box is blank (no video). Loading spinner showed first, then blank. Reproduces on
every iOS browser; never on desktop Chromium.

**Root cause:** The viewport was an outer CSS grid with `place-items-center`
(= `justify-items: center`). A grid with center justification sizes its in-flow
item to **content width**. The active branch's only children were
absolutely-positioned (`<a-scene>`, scan overlays) → zero intrinsic width → WebKit
collapsed the container, `a-scene`, `<video>` and `<canvas>` all to `width: 0`.
Chromium happened to keep a width, so it never repro'd there.

Measured proof (Playwright WebKit, after scene mount): `a-scene` rect
`width: 0, height: 261`; ancestor walk showed the grid cell was full width (348)
but the in-flow child branch was `width: 0`.

**Fix:** Make the AR-active branch containers **fill the positioned parent with
`absolute inset-0`** instead of in-flow `relative h-full min-h-[...]`. This is the
exact pattern a `next/image` with `fill` already uses (and which always rendered).

```diff
- <div className="relative h-full min-h-[240px] overflow-hidden bg-[#211d18]">
+ <div className="absolute inset-0 overflow-hidden bg-[#211d18]">
    <ArImageTrackingScene ... />
```

Apply to every branch whose children are all absolutely-positioned (scanning,
guardian, wish, loading, fallback). The parent stays `relative` with
`aspect-[4/3]` (aspect-ratio gives it a definite height even with only absolute
children — verified in WebKit).

**General lesson:** absolutely-positioned-only content + a content-sized container
= 0 width in WebKit. Don't rely on `grid place-items-center` to give width to a
box whose content is all `position:absolute`. Fill via `absolute inset-0` off a
positioned ancestor, or give the grid column an explicit `1fr`/width.

---

## 2. `next/image` renders blank on some iOS versions

**Symptom:** A preview image shows in Chromium but is blank on the iPhone, while
the raw asset 200s fine via `curl`.

**Root cause:** `next/image` serves through `/_next/image` with AVIF/WebP format
negotiation (`images.formats`). On some iOS versions the optimized/negotiated
image fails to decode/render. (A `curl` without an `Accept: image/avif` header
gets a PNG and looks fine, masking the issue.)

**Fix (for pre-sized art):** `next.config` → `images: { unoptimized: true }`. The
component renders a plain `<img src="/path.png">`, no optimizer, no AVIF. The app's
images were already sized for display, so optimization bought nothing.

**Watch-outs when redeploying this fix:**
- Production `next start` caches the build in `.next`; if the old server process
  is still bound to the port, you keep serving the old optimized HTML. Verify the
  served HTML actually contains the raw `/path.png` (not `/_next/image?...`).
- Confirm with `curl` on the deployed URL, and re-check via WebKit, before
  concluding the fix is live.

---

## 3. Gyro / DeviceOrientation never fires on iOS 13+

**Symptom:** Tilt-to-look (parallax/space browse) does nothing on iPhone; works on
Android.

**Root cause:** iOS 13+ requires `DeviceOrientationEvent.requestPermission()` to be
called from a **user gesture** before any `deviceorientation` events fire.

**Fix:** Detect the requirement and gate behind a tap; always keep touch-drag.

```ts
export function deviceOrientationRequiresPermission(): boolean {
  const ctor = (window as any)?.DeviceOrientationEvent;
  return typeof ctor?.requestPermission === "function"; // true on iOS 13+
}
export async function requestDeviceOrientationPermission() {
  const ctor = (window as any)?.DeviceOrientationEvent;
  if (typeof ctor?.requestPermission !== "function") return "unsupported";
  try { return (await ctor.requestPermission()) === "granted" ? "granted" : "denied"; }
  catch { return "denied"; }
}
```
Only attach `window.addEventListener("deviceorientation", ...)` once granted;
surface an "开启体感浏览" button when permission is needed; pointer-drag is the
fallback so the feature is never dead.

---

## 4. Camera "appears then black" / not visible inside the a-scene

**Root causes & mitigations:**
- MindAR's injected `<video>` must stay visible — force it visible with CSS in the
  scene wrapper (`video { position:absolute; inset:0; width:100%; height:100%;
  object-fit:cover; opacity:1 !important; visibility:visible !important; }`) and
  make the `a-scene`/canvas backgrounds transparent.
- React effect cleanup can `stop()` MindAR: if the effect that wires
  `targetFound/targetLost/arReady/arError` depends on inline callbacks, it re-runs
  on every render and tears the tracker down. **Store callbacks in a `ref`** and
  give the listener-effect an empty dep array so it mounts once. Provide a
  `safelyTearDownScene()` that stops the `mindar-image-system`, pauses the scene,
  and disposes the renderer — wrapped in try/catch (partial-init paths throw).
- iOS autoplay: MindAR sets `playsinline`/muted; if you hand-roll video, add them.

---

## 5. Fullscreen AR (camera too small in an embedded box)

When the camera is active, promote the viewport to fullscreen instead of an
`aspect-[4/3]` box:
- AR-active container → `fixed inset-0 z-40 bg-black`; the `absolute inset-0`
  scene fills the screen.
- Controls → a bottom sheet: `fixed inset-x-0 bottom-0 z-50 ... rounded-t-2xl
  bg-.../95 backdrop-blur` with `pb-[calc(1rem+env(safe-area-inset-bottom))]` and
  `overflow-y-auto max-h-[55vh]`.
- Hide page title/story while fullscreen; add an exit (✕) button positioned with
  `top: calc(env(safe-area-inset-top) + 0.75rem)`.
- Caveat: if an ancestor has a `transform/filter/will-change`, `position:fixed`
  becomes relative to that ancestor, not the viewport. On a phone-width container
  it still looks fullscreen; if not, portal the layer to `document.body`.

---

## Quick triage table

| Symptom on iPhone | First suspect | Fix |
|---|---|---|
| Blank camera after "start AR", spinner first | scene `width:0` (grid `place-items-center`) | `absolute inset-0` containers (#1) |
| Preview/static image blank, fine in Chrome | `next/image` AVIF/optimizer | `images.unoptimized` (#2) |
| Tilt-to-look dead | DeviceOrientation permission | gesture-bound `requestPermission` (#3) |
| Camera flashes then black | effect cleanup stops MindAR / video hidden | callbacks in ref + camera-visible CSS (#4) |
| Effect too small | embedded box | fullscreen `fixed inset-0` + bottom sheet (#5) |
| Stuck on "正在接入" spinner forever | heavy vendor scripts still downloading (slow net) | wait longer / check the `<script>` onload, not a bug |
