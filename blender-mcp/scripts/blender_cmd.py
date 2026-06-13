#!/usr/bin/env python3
"""Drive the running Blender (blender-mcp addon socket on localhost:9876).

Usage:
  python blender_cmd.py scene                 # get_scene_info
  python blender_cmd.py exec <python_file>    # run Python inside Blender (execute_code)
  python blender_cmd.py shot <out.png>        # grab a viewport screenshot

The addon protocol is raw JSON over a socket: {"type":..., "params":{...}} →
{"status":"success"|"error", "result"|"message": ...}.
"""
import socket, json, sys, base64

def cmd(t, params=None, host="localhost", port=9876, timeout=180):
    s = socket.socket(); s.settimeout(timeout); s.connect((host, port))
    s.sendall(json.dumps({"type": t, "params": params or {}}).encode("utf-8"))
    buf = b""
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
        try:
            r = json.loads(buf.decode("utf-8")); s.close(); return r
        except Exception:
            continue
    s.close()
    return json.loads(buf.decode("utf-8"))

if __name__ == "__main__":
    op = sys.argv[1]
    if op == "scene":
        print(json.dumps(cmd("get_scene_info"), ensure_ascii=False, indent=1)[:6000])
    elif op == "exec":
        r = cmd("execute_code", {"code": open(sys.argv[2], encoding="utf-8").read()})
        res = r.get("result", {})
        out = res.get("result") if isinstance(res, dict) else res
        print("STATUS:", r.get("status"))
        print(out or r.get("message"))
    elif op == "shot":
        r = cmd("get_viewport_screenshot", {"max_size": 1024})
        res = r.get("result", {})
        b64 = res.get("data") or res.get("image") if isinstance(res, dict) else None
        if b64:
            open(sys.argv[2], "wb").write(base64.b64decode(b64))
            print("saved", sys.argv[2])
        else:
            print(json.dumps(r)[:1000])
