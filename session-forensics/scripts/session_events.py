#!/usr/bin/env python3
"""Normalized event layer over Codex / Claude Code / Kimi Code session logs.

Everything above this file — the two flows, the signatures, the gates — is
platform independent. The only per-platform work is turning one raw record into
zero or more normalized events, which is what this module does.

    Event(line, flow, kind, name, size, text, extra)

    flow  narrative | evidence | lifecycle | meta
    kind  user_msg | assistant_msg | thinking | tool_call | tool_output
          | compaction | turn_complete | turn_aborted | token_count
          | session_meta | subagent

Field notes that matter downstream:
    tool_call    name = tool name, text = raw arguments (patch targets and shell
                 commands are extracted from it by the caller)
    tool_output  name = the tool that produced it, text = output, size = len(output)
    token_count  size = context length for that request
    extra        platform specifics (window size, agent path, subtype, ...)

Verified against real corpora on 2026-07. Every field below was observed, not
assumed — see references/platforms.md for the probe results.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator


@dataclass
class Event:
    line: int
    flow: str
    kind: str
    name: str = ""
    size: int = 0
    text: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# format detection
# --------------------------------------------------------------------------- #

def detect_format(path: Path, probe_lines: int = 60) -> str:
    """Sniff the log format. Cheap: reads at most `probe_lines` lines."""
    votes = {"codex": 0, "claude_code": 0, "kimi": 0}
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for i, line in enumerate(handle):
            if i >= probe_lines:
                break
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            t = rec.get("type") or ""
            if t in ("response_item", "event_msg", "session_meta", "turn_context", "compacted"):
                votes["codex"] += 1
            elif t in ("user", "assistant", "system", "attachment", "ai-title", "last-prompt"):
                votes["claude_code"] += 1
            elif t.startswith(("context.", "usage.", "turn.", "tools.", "permission.", "config.")):
                votes["kimi"] += 1
    best = max(votes, key=lambda k: votes[k])
    return best if votes[best] else "unknown"


# --------------------------------------------------------------------------- #
# Codex
# --------------------------------------------------------------------------- #

def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for item in content:
            if isinstance(item, dict):
                v = item.get("text") or item.get("input_text")
                if isinstance(v, str):
                    out.append(v)
            elif isinstance(item, str):
                out.append(item)
        return "\n".join(out)
    return ""


def _codex_events(rec: dict[str, Any], line: int) -> Iterator[Event]:
    rtype = rec.get("type")
    if rtype == "compacted":
        yield Event(line, "lifecycle", "compaction")
        return
    if rtype == "session_meta":
        yield Event(line, "meta", "session_meta")
        return

    payload = rec.get("payload")
    if not isinstance(payload, dict):
        return
    ptype = payload.get("type")

    if rtype == "response_item":
        if ptype == "message":
            role = payload.get("role")
            body = _text_of(payload.get("content"))
            if role == "assistant":
                yield Event(line, "narrative", "assistant_msg", text=body)
            elif role == "user":
                yield Event(line, "evidence", "user_msg", text=body)
        elif ptype == "reasoning":
            yield Event(line, "narrative", "thinking")
        elif ptype in ("function_call", "custom_tool_call"):
            raw = payload.get("arguments") or payload.get("input") or ""
            if not isinstance(raw, str):
                raw = json.dumps(raw, ensure_ascii=False)
            yield Event(line, "evidence", "tool_call", name=payload.get("name") or "?", text=raw)
        elif ptype in ("function_call_output", "custom_tool_call_output"):
            out = str(payload.get("output") or "")
            yield Event(line, "evidence", "tool_output", size=len(out), text=out)

    elif rtype == "event_msg":
        if ptype == "sub_agent_activity":
            yield Event(line, "meta", "subagent", name=str(payload.get("agent_path") or "?"),
                        extra={"thread": payload.get("agent_thread_id")})
        elif ptype == "token_count":
            info = payload.get("info") or {}
            val = (info.get("last_token_usage") or {}).get("input_tokens")
            if isinstance(val, int) and val > 0:
                yield Event(line, "meta", "token_count", size=val,
                            extra={"window": info.get("model_context_window")})
        elif ptype == "task_complete":
            yield Event(line, "lifecycle", "turn_complete")
        elif ptype in ("turn_aborted", "thread_rolled_back"):
            yield Event(line, "lifecycle", "turn_aborted", name=ptype)


# --------------------------------------------------------------------------- #
# Claude Code
# --------------------------------------------------------------------------- #

# Observed: compaction is a system record with subtype=compact_boundary, and the
# summary record carries isCompactSummary=True + compactMetadata.trigger.
# There is no task_started/task_complete pair like Codex has; stop_hook_summary is
# the closest turn-end marker and api_error the closest abort marker.
_CC_PATCH_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
_CC_EXEC_TOOLS = {"Bash", "BashOutput"}


def _claude_events(rec: dict[str, Any], line: int) -> Iterator[Event]:
    rtype = rec.get("type")

    if rec.get("isCompactSummary") is True:
        yield Event(line, "lifecycle", "compaction",
                    extra={"trigger": (rec.get("compactMetadata") or {}).get("trigger")})
        return

    if rtype == "system":
        sub = rec.get("subtype")
        if sub == "compact_boundary":
            yield Event(line, "lifecycle", "compaction", extra={"trigger": "boundary"})
        elif sub == "stop_hook_summary":
            yield Event(line, "lifecycle", "turn_complete")
        elif sub in ("api_error", "model_refusal_fallback"):
            yield Event(line, "lifecycle", "turn_aborted", name=str(sub))
        return

    if rtype in ("ai-title", "last-prompt", "queue-operation", "mode", "custom-title"):
        # UI bookkeeping, NOT an embedded session. Codex's session_meta means
        # "another thread was inlined here"; emitting these under the same kind
        # would make a Claude Code session look like it contained 573 subthreads.
        # Same name, different meaning across platforms = definition drift.
        yield Event(line, "meta", "ui_noise", name=str(rtype))
        return

    if rec.get("isSidechain"):
        yield Event(line, "meta", "subagent", name=str(rec.get("sessionId") or "?"))

    msg = rec.get("message")
    if not isinstance(msg, dict):
        return

    usage = msg.get("usage")
    if isinstance(usage, dict):
        ctx = sum(int(usage.get(k) or 0) for k in
                  ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        if ctx > 0:
            yield Event(line, "meta", "token_count", size=ctx, extra={"window": None})

    role = msg.get("role")
    content = msg.get("content")
    if isinstance(content, str):
        content = [{"type": "text", "text": content}]
    if not isinstance(content, list):
        return

    for item in content:
        if not isinstance(item, dict):
            continue
        itype = item.get("type")
        if itype == "text":
            body = str(item.get("text") or "")
            if role == "assistant":
                yield Event(line, "narrative", "assistant_msg", text=body)
            else:
                yield Event(line, "evidence", "user_msg", text=body)
        elif itype == "thinking":
            yield Event(line, "narrative", "thinking")
        elif itype == "tool_use":
            name = str(item.get("name") or "?")
            args = item.get("input")
            raw = json.dumps(args, ensure_ascii=False) if not isinstance(args, str) else args
            targets = []
            if name in _CC_PATCH_TOOLS and isinstance(args, dict):
                fp = args.get("file_path") or args.get("notebook_path")
                if isinstance(fp, str):
                    targets.append(fp)
            cmd = args.get("command") if (name in _CC_EXEC_TOOLS and isinstance(args, dict)) else None
            yield Event(line, "evidence", "tool_call", name=name, text=raw,
                        extra={"patch_targets": targets, "command": cmd,
                               "is_exec": name in _CC_EXEC_TOOLS})
        elif itype == "tool_result":
            body = item.get("content")
            out = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
            yield Event(line, "evidence", "tool_output", size=len(out), text=out)
        elif itype == "image":
            src = item.get("source") or {}
            data = src.get("data") if isinstance(src, dict) else None
            n = len(data) if isinstance(data, str) else 0
            yield Event(line, "evidence", "tool_output", name="image", size=n, text="")


# --------------------------------------------------------------------------- #
# Kimi Code
# --------------------------------------------------------------------------- #

# Kimi writes one wire.jsonl per agent under
#   sessions/<workspace>/session_<uuid>/agents/<agent>/wire.jsonl
# so subagents live in SEPARATE FILES, unlike Codex (inlined) and Claude Code
# (isSidechain in the same file). Callers wanting the full picture must walk the
# agents/ directory; a single wire.jsonl is one agent's view.
#
# ⚠️ No compaction marker was observed in the probed corpus. Until one is found,
# every compression-derived conclusion must be reported as UNAVAILABLE for Kimi
# rather than silently computed as zero.
_KIMI_PATCH_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "apply_patch"}
_KIMI_EXEC_TOOLS = {"Bash", "Shell", "Exec", "run_command"}


def _kimi_events(rec: dict[str, Any], line: int) -> Iterator[Event]:
    rtype = rec.get("type") or ""

    if rtype == "metadata":
        yield Event(line, "meta", "session_meta")
        return

    if rtype == "turn.prompt":
        body = rec.get("prompt") or rec.get("text") or ""
        if not isinstance(body, str):
            body = json.dumps(body, ensure_ascii=False)
        yield Event(line, "evidence", "user_msg", text=body)
        return

    if rtype == "context.append_message":
        msg = rec.get("message") if isinstance(rec.get("message"), dict) else rec
        role = msg.get("role")
        body = _text_of(msg.get("content"))
        if role == "user":
            yield Event(line, "evidence", "user_msg", text=body)
        elif role == "assistant":
            yield Event(line, "narrative", "assistant_msg", text=body)
        return

    if rtype != "context.append_loop_event":
        return

    ev = rec.get("event")
    if not isinstance(ev, dict):
        return
    etype = ev.get("type")

    if etype == "tool.call":
        name = str(ev.get("name") or "?")
        call_id = ev.get("toolCallId")
        args = ev.get("args")
        raw = json.dumps(args, ensure_ascii=False) if not isinstance(args, str) else args
        targets = []
        if name in _KIMI_PATCH_TOOLS and isinstance(args, dict):
            fp = args.get("path") or args.get("file_path")
            if isinstance(fp, str):
                targets.append(fp)
        cmd = args.get("command") if (name in _KIMI_EXEC_TOOLS and isinstance(args, dict)) else None
        yield Event(line, "evidence", "tool_call", name=name, text=raw,
                    extra={"patch_targets": targets, "command": cmd,
                           "is_exec": name in _KIMI_EXEC_TOOLS,
                           "call_id": call_id})
    elif etype == "tool.result":
        call_id = ev.get("toolCallId")
        res = ev.get("result")
        out = res.get("output") if isinstance(res, dict) else res
        out = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
        yield Event(line, "evidence", "tool_output", size=len(out), text=out,
                    extra={"call_id": call_id})
    elif etype == "content.part":
        part = ev.get("part") or {}
        ptype = part.get("type")
        if ptype == "think":
            yield Event(line, "narrative", "thinking")
        elif ptype == "text":
            yield Event(line, "narrative", "assistant_msg", text=str(part.get("text") or ""))
    elif etype == "step.end":
        usage = ev.get("usage") or {}
        ctx = sum(int(usage.get(k) or 0) for k in
                  ("inputOther", "inputCacheRead", "inputCacheCreation"))
        if ctx > 0:
            yield Event(line, "meta", "token_count", size=ctx, extra={"window": None})
        if ev.get("finishReason") in ("stop", "end_turn"):
            yield Event(line, "lifecycle", "turn_complete")
        elif ev.get("finishReason") in ("aborted", "cancelled", "error"):
            yield Event(line, "lifecycle", "turn_aborted", name=str(ev.get("finishReason")))


_ADAPTERS = {"codex": _codex_events, "claude_code": _claude_events, "kimi": _kimi_events}

# Capabilities each platform can actually support. A metric whose inputs are not
# observable on a platform must be reported as unavailable, never as zero — a
# silent zero for "compactions" would make a Kimi session look pristine.
CAPABILITIES = {
    "codex":       {"compaction": True,  "turn_lifecycle": True,  "context_window": True,
                    "subagents": "inline"},
    "claude_code": {"compaction": True,  "turn_lifecycle": "approx", "context_window": False,
                    "subagents": "sidechain"},
    "kimi":        {"compaction": False, "turn_lifecycle": "approx", "context_window": False,
                    "subagents": "separate-files"},
}


def iter_events(path: Path, max_lines: int | None = None,
                fmt: str | None = None) -> Iterator[Event]:
    fmt = fmt or detect_format(path)
    adapter = _ADAPTERS.get(fmt)
    if adapter is None:
        raise ValueError(f"unsupported session format: {fmt} ({path})")
    seen = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, raw in enumerate(handle, start=1):
            if max_lines and line_no > max_lines:
                break
            seen = line_no
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                yield Event(line_no, "meta", "malformed")
                continue
            if not isinstance(rec, dict):
                yield Event(line_no, "meta", "malformed")
                continue
            yield from adapter(rec, line_no)
    # Terminal marker: lines that produce no events still count toward file length,
    # so the caller cannot derive the true line count from events alone.
    yield Event(seen, "meta", "eof", extra={"format": fmt})


if __name__ == "__main__":
    import sys
    from collections import Counter

    for arg in sys.argv[1:]:
        p = Path(arg).expanduser()
        fmt = detect_format(p)
        kinds: Counter[str] = Counter()
        tools: Counter[str] = Counter()
        last = 0
        for e in iter_events(p):
            kinds[f"{e.flow}/{e.kind}"] += 1
            if e.kind == "tool_call":
                tools[e.name] += 1
            last = e.line
        print(f"\n{p.name}  format={fmt}  lines={last}")
        print(f"  capabilities: {CAPABILITIES.get(fmt)}")
        for k, v in kinds.most_common(12):
            print(f"    {k:<26} {v}")
        print(f"    tools: {dict(tools.most_common(6))}")
