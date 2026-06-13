#!/usr/bin/env node
/*
 * Reproduce iOS-WebKit-only WebAR bugs on the desktop, with a fake camera.
 * WebKit == Safari's engine, so this catches iOS-only failures that desktop
 * Chromium never shows (blank camera, width:0 collapse, etc.).
 *
 * Setup (once):
 *   mkdir -p /tmp/wktest && cd /tmp/wktest && npm init -y && npm i playwright
 *   npx playwright install webkit   # must match the installed playwright version
 *
 * Usage:
 *   node webkit-repro.mjs <url> [--start "开启 AR"] [--wait 22000] [--width-walk] [--shot out.png]
 *
 *   --start       button text to click to enter AR (default: "开启 AR"); omit with --start ""
 *   --wait        ms to wait after clicking, for the heavy A-Frame/MindAR scripts to load (default 22000)
 *   --width-walk  after mount, walk a-scene's ancestors logging widths (find the collapsing element)
 *   --shot        screenshot path (default /tmp/wk_repro.png)
 *
 * Prints: console/page errors, phase hints, and a-scene/video/canvas rects
 * (width:0 == the collapse bug).
 */
import { webkit, devices } from 'playwright';

const args = process.argv.slice(2);
const url = args[0];
if (!url) { console.error('usage: node webkit-repro.mjs <url> [opts]'); process.exit(1); }
const opt = (flag, def) => { const i = args.indexOf(flag); return i >= 0 ? args[i + 1] : def; };
const startText = args.includes('--start') ? opt('--start', '') : '开启 AR';
const waitMs = parseInt(opt('--wait', '22000'), 10);
const widthWalk = args.includes('--width-walk');
const shot = opt('--shot', '/tmp/wk_repro.png');

const logs = [];
const browser = await webkit.launch();
const ctx = await browser.newContext({ ...devices['iPhone 13'] });

// Fake camera: WebKit has no fake-device flag and grantPermissions(['camera']) throws,
// so override getUserMedia to return a synthetic canvas stream.
await ctx.addInitScript(() => {
  const c = document.createElement('canvas'); c.width = 640; c.height = 480;
  const g = c.getContext('2d');
  (function draw(){ g.fillStyle='#1d3b53'; g.fillRect(0,0,640,480);
    g.fillStyle='#e8cc7e'; g.fillRect(Math.random()*560, Math.random()*400, 60, 60);
    requestAnimationFrame(draw); })();
  const stream = c.captureStream(15);
  if (navigator.mediaDevices) {
    navigator.mediaDevices.getUserMedia = async () => stream;
    navigator.mediaDevices.enumerateDevices = async () => [{ kind:'videoinput', deviceId:'fake', label:'fake', groupId:'g' }];
  }
});

const page = await ctx.newPage();
page.on('console', m => logs.push(`[${m.type()}] ${m.text()}`.slice(0, 350)));
page.on('pageerror', e => logs.push(`PAGEERROR: ${e.message} | ${(e.stack||'').split('\n').slice(1,3).join(' ')}`));
page.on('requestfailed', r => logs.push(`REQFAIL: ${r.url().split('/').slice(-1)[0].slice(0,55)} :: ${r.failure()?.errorText}`));

try { await page.goto(url, { waitUntil: 'load', timeout: 60000 }); }
catch (e) { logs.push('GOTO_ERR: ' + e.message); }
await page.waitForTimeout(1500);

if (startText) {
  const clicked = await page.evaluate((t) => {
    const b = [...document.querySelectorAll('button')].find(x => x.textContent.includes(t));
    if (b) { b.click(); return true; } return false;
  }, startText);
  logs.push(`clicked "${startText}": ${clicked}`);
  await page.waitForTimeout(waitMs);
}

const info = await page.evaluate(() => {
  const rect = (el) => el ? (r => ({ w: Math.round(r.width), h: Math.round(r.height), top: Math.round(r.top), left: Math.round(r.left) }))(el.getBoundingClientRect()) : null;
  const a = document.querySelector('a-scene');
  const v = document.querySelector('video');
  const cv = document.querySelector('a-scene canvas, canvas');
  const t = document.body.innerText;
  return {
    viewport: [innerWidth, innerHeight],
    aframeLoaded: typeof window.AFRAME !== 'undefined',
    arScripts: [...document.querySelectorAll('script[src*="/vendor/ar/"]')].map(s => s.src.split('/').pop()),
    aSceneRect: rect(a),
    videoRect: rect(v),
    canvas: cv ? { w: cv.width, h: cv.height } : null,
    phaseHints: ['正在接入','请对准','已识别','切换演示','当前使用'].filter(s => t.includes(s)),
  };
});

let walk = null;
if (widthWalk) {
  walk = await page.evaluate(() => {
    const el = document.querySelector('a-scene'); if (!el) return ['NO a-scene'];
    const out = []; let n = el, i = 0;
    while (n && n !== document.body && i < 10) {
      const r = n.getBoundingClientRect(); const cs = getComputedStyle(n);
      out.push(`${i} <${n.tagName.toLowerCase()} class="${(n.className||'').toString().slice(0,40)}"> w=${Math.round(r.width)} h=${Math.round(r.height)} disp=${cs.display} pos=${cs.position} justifyItems=${cs.justifyItems}`);
      n = n.parentElement; i++;
    }
    return out;
  });
}

await page.screenshot({ path: shot });
console.log('=== CONSOLE / ERRORS ===\n' + (logs.length ? logs.join('\n') : '(none)'));
console.log('\n=== STATE ===\n' + JSON.stringify(info, null, 1));
if (walk) console.log('\n=== ANCESTOR WIDTH WALK (find the width:0 element) ===\n' + walk.join('\n'));
console.log('\nscreenshot: ' + shot);
await browser.close();
