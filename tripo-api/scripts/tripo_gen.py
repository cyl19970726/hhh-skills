#!/usr/bin/env python3
"""Drive the Tripo API: upload image -> image_to_model -> poll -> download.

Reusable across stages (image_to_model / rig / animate). Key read from
worktree-local .tripo-key (gitignored) or TRIPO_KEY env.
"""
import sys, os, time, json, pathlib, urllib.request

BASE = "https://api.tripo3d.ai/v2/openapi"
ROOT = pathlib.Path(__file__).resolve().parent.parent

# Tripo 3.x is a generation-network step-change over 2.5 (geometry + texture).
# Omitting model_version makes the API fall back to its default — confirmed = v2.5-20250123
# (docs.tripo3d.ai) — exactly how tasks quietly downgraded. Every geometry-generating task
# MUST resolve through here: pin >=3.x, print, assert.
# Known versions (2026-06): v3.1-20260211 (latest 3.x, "recommended"), v3.0-20250812,
# v2.5-20250123 (API DEFAULT — bad), v2.0, v1.4, Turbo-v1.0, P1-20260311 (newer line, unverified).
DEFAULT_MODEL = "v3.1-20260211"

MIN_MAJOR = 3  # provisional floor: 2.5/below silently downgrade quality. Raise as Tripo ships.

def resolve_model(v):
    v = v or DEFAULT_MODEL
    # Floor, not allowlist: reject 2.x-and-below, but DON'T reject future numeric majors (v4+).
    # Caveat: a non-numeric line like "P1-*" parses to -1 and is rejected here — intentional
    # for now (unverified); revisit if P1 proves superior. Knowledge is provisional.
    try:
        major = int(v.lstrip("v").split(".")[0])
    except ValueError:
        major = -1
    assert major >= MIN_MAJOR, (
        f"refusing model_version {v!r}: must be Tripo >= {MIN_MAJOR}.x "
        f"— 2.5/below silently downgrades quality (API default is v2.5!)"
    )
    print("| model_version:", v, flush=True)
    return v

def mesh_opts():
    """Geometry/mesh-mode flags via env (keeps positional CLI simple). These were NEVER set
    historically → all past assets ran in the DEFAULT 'standard' geometry mode, a second
    quality downgrade on top of the 2.5 one. For hero/character assets set
    TRIPO_GEOMETRY_QUALITY=detailed; quad gives rig-friendlier topology. See INV-TRIPO-MESH."""
    o = {}
    gq = os.environ.get("TRIPO_GEOMETRY_QUALITY")          # standard | detailed
    if gq: o["geometry_quality"] = gq
    tq = os.environ.get("TRIPO_TEXTURE_QUALITY")           # standard | detailed
    if tq: o["texture_quality"] = tq
    if os.environ.get("TRIPO_QUAD") == "1": o["quad"] = True            # quad remeshing (clean topo, +rig)
    if os.environ.get("TRIPO_SMART_LOWPOLY") == "1": o["smart_low_poly"] = True
    st = os.environ.get("TRIPO_STYLE")                     # e.g. person:person2cartoon (used for 揭小贤 v6c)
    if st: o["style"] = st
    fl = os.environ.get("TRIPO_FACE_LIMIT")
    if fl: o["face_limit"] = int(fl)
    if o: print("| mesh_opts:", o, flush=True)
    return o

def key():
    k = os.environ.get("TRIPO_KEY")
    if not k:
        kf = ROOT / ".tripo-key"
        k = kf.read_text().strip() if kf.exists() else ""
    if not k:
        sys.exit("no Tripo key")
    return k

import requests
H = {"Authorization": f"Bearer {key()}"}

def _retry(fn, tries=6, wait=4):
    """Network here is behind a flaky proxy; retry transient errors."""
    for i in range(tries):
        try:
            return fn()
        except (requests.exceptions.RequestException,) as e:
            if i == tries - 1:
                raise
            print(f"  net retry {i+1}/{tries}: {type(e).__name__}", flush=True)
            time.sleep(wait)

def upload(path):
    def go():
        with open(path, "rb") as f:
            r = requests.post(f"{BASE}/upload", headers=H, files={"file": f}, timeout=60)
        r.raise_for_status()
        return r.json()
    d = _retry(go)
    assert d["code"] == 0, d
    return d["data"]["image_token"]

def create(payload):
    def go():
        return requests.post(f"{BASE}/task", headers={**H, "Content-Type": "application/json"},
                             data=json.dumps(payload), timeout=60).json()
    d = _retry(go)
    assert d.get("code") == 0, d
    return d["data"]["task_id"]

def poll(task_id, timeout=600):
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        d = _retry(lambda: requests.get(f"{BASE}/task/{task_id}", headers=H, timeout=60).json())["data"]
        st, prog = d["status"], d.get("progress", 0)
        if (st, prog) != last:
            print(f"  [{int(time.time()-t0):3d}s] {st} {prog}%", flush=True)
            last = (st, prog)
        if st == "success":
            return d
        if st in ("failed", "cancelled", "unknown", "banned", "expired"):
            sys.exit(f"task {st}: {json.dumps(d)[:500]}")
        time.sleep(6)
    sys.exit("poll timeout")

def fetch(url, out):
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, out)
    print("  saved", out, f"({os.path.getsize(out)/1e6:.2f} MB)")

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "i2m":  # image_to_model: <image_path> <out_glb> [model_version] [texture_quality]
        img, out = sys.argv[2], sys.argv[3]
        model_version = resolve_model(sys.argv[4] if len(sys.argv) > 4 else None)
        texture_quality = sys.argv[5] if len(sys.argv) > 5 else None  # "HD" rejected by API; default standard
        tok = upload(img)
        print("image_token:", tok, "| tex:", texture_quality or "standard")
        payload = {
            "type": "image_to_model",
            "file": {"type": "png", "file_token": tok},
            "model_version": model_version,
            "texture": True, "pbr": True,
        }
        if texture_quality:
            payload["texture_quality"] = texture_quality
        payload.update(mesh_opts())
        tid = create(payload)
        print("task_id:", tid)
        d = poll(tid)
        out_obj = d.get("output", {})
        print("output keys:", list(out_obj.keys()))
        model_url = out_obj.get("pbr_model") or out_obj.get("model")
        if model_url:
            fetch(model_url, out)
        rimg = out_obj.get("rendered_image")
        if rimg:
            fetch(rimg, out.replace(".glb", "-render.webp"))
        print("TASK_ID", tid)
    elif cmd == "mv4":  # multiview_to_model from 4 separate views: <front> <left> <back> <right> <out_glb> [model_version]
        front, left, back, right, out = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]
        model_version = resolve_model(sys.argv[7] if len(sys.argv) > 7 else None)
        tf, tl, tb, tr = upload(front), upload(left), upload(back), upload(right)
        tid = create({
            "type": "multiview_to_model",
            "model_version": model_version,
            "files": [
                {"type": "png", "file_token": tf},
                {"type": "png", "file_token": tl},
                {"type": "png", "file_token": tb},
                {"type": "png", "file_token": tr},
            ],
            "texture": True, "pbr": True,
            **mesh_opts(),
        })
        print("task_id:", tid)
        d = poll(tid, timeout=1500)
        o = d.get("output", {})
        print("output keys:", list(o.keys()))
        url = o.get("pbr_model") or o.get("model")
        if url:
            fetch(url, out)
        if o.get("rendered_image"):
            fetch(o["rendered_image"], out.replace(".glb", "-render.webp"))
        print("TASK_ID", tid)
    elif cmd == "mv":  # multiview_to_model: <front> <side> <back> <out_glb> [model_version]
        front, side, back, out = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
        model_version = resolve_model(sys.argv[6] if len(sys.argv) > 6 else None)
        tf, ts, tb = upload(front), upload(side), upload(back)
        print("tokens:", tf[:8], ts[:8], tb[:8])
        # Tripo multiview slots are [front, left, back, right]; we have front/side/back
        tid = create({
            "type": "multiview_to_model",
            "model_version": model_version,
            "files": [
                {"type": "png", "file_token": tf},
                {"type": "png", "file_token": ts},
                {"type": "png", "file_token": tb},
                {},
            ],
            "texture": True, "pbr": True,
            **mesh_opts(),
        })
        print("task_id:", tid)
        d = poll(tid, timeout=1500)
        o = d.get("output", {})
        print("output keys:", list(o.keys()))
        url = o.get("pbr_model") or o.get("model")
        if url:
            fetch(url, out)
        if o.get("rendered_image"):
            fetch(o["rendered_image"], out.replace(".glb", "-render.webp"))
        print("TASK_ID", tid)
    elif cmd == "get":  # poll existing task + download: <task_id> <out_glb>
        tid, out = sys.argv[2], sys.argv[3]
        d = poll(tid)
        o = d.get("output", {})
        print("output keys:", list(o.keys()))
        mu = o.get("pbr_model") or o.get("model")
        if mu:
            fetch(mu, out)
        if o.get("rendered_image"):
            fetch(o["rendered_image"], out.replace(".glb", "-render.webp"))
    elif cmd == "prerig":  # check riggability: <orig_model_task_id>
        tid = create({"type": "animate_prerigcheck", "original_model_task_id": sys.argv[2]})
        print("prerig task:", tid)
        d = poll(tid)
        print("RIGGABLE:", d.get("output", {}).get("riggable"), "| output:", d.get("output"))
    elif cmd == "rig":  # auto-rig: <orig_model_task_id> <out_glb> [spec]
        orig, out = sys.argv[2], sys.argv[3]
        spec = sys.argv[4] if len(sys.argv) > 4 else "mixamo"
        tid = create({"type": "animate_rig", "original_model_task_id": orig,
                      "out_format": "glb", "spec": spec})
        print("rig task:", tid)
        d = poll(tid, timeout=1500)
        o = d.get("output", {})
        print("output keys:", list(o.keys()))
        url = o.get("model") or o.get("pbr_model") or o.get("rigged_model")
        if url:
            fetch(url, out)
        print("TASK_ID", tid)
    elif cmd == "animate":  # retarget preset anim: <rig_model_task_id> <preset> <out_glb>
        rig_tid, preset, out = sys.argv[2], sys.argv[3], sys.argv[4]
        tid = create({"type": "animate_retarget", "original_model_task_id": rig_tid,
                      "out_format": "glb", "animation": preset})
        print("animate task:", tid)
        d = poll(tid, timeout=1500)
        o = d.get("output", {})
        print("output keys:", list(o.keys()))
        url = o.get("model") or o.get("pbr_model")
        if url:
            fetch(url, out)
        print("TASK_ID", tid)
    elif cmd == "status":
        print(json.dumps(poll(sys.argv[2]), indent=2)[:2000])
    elif cmd == "balance":
        print(requests.get(f"{BASE}/user/balance", headers=H).json())
    else:
        sys.exit(f"unknown cmd {cmd}")
