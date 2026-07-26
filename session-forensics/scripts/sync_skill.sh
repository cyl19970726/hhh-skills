#!/usr/bin/env bash
# Propagate this skill from the authoritative source to its derived copies.
#
# Why this exists as a harness and not as a note in gates.md:
# the same failure recurred three times, twice on the same day, by the same
# person who had just written the gate.
#
#   n=1  scratchpad/session_metrics.py (307 lines) coexisted with the skill copy
#        (473 lines) — the draft was 166 lines behind
#   n=2  019f9a28: source patched three more times after the last rsync -> 4 files
#        diverged, and TWO ALREADY-FALSIFIED CONCLUSIONS stayed live in the Codex
#        global copy and on GitHub
#   n=3  same session, hours after G0 was written: self-upgrade.md +
#        session_metrics.py diverged again, uncommitted
#
# A gate that says "remember to run the comparison" is executed by discipline.
# Discipline failed three times. The check has to refuse to proceed instead.
#
# Usage:
#   sync_skill.sh              sync + verify, no git action
#   sync_skill.sh --check      verify only, change nothing (exit 1 if diverged)
#   sync_skill.sh --commit "<msg>"   sync + verify + stage ONLY the skill path + commit
#   sync_skill.sh --commit "<msg>" --push   ... and push, then verify HEAD == origin/main
set -uo pipefail

SRC=${SESSION_FORENSICS_SRC:-/Users/hhh0x/.claude/skills/session-forensics}
CODEX=${SESSION_FORENSICS_CODEX:-/Users/hhh0x/.codex/skills/session-forensics}
REPO=${SESSION_FORENSICS_REPO:-/Users/hhh0x/hhh-skills}
SUBPATH=$(basename "$SRC")
PUB="$REPO/$SUBPATH"
EXCL=(--exclude 'local/' --exclude '__pycache__/' --exclude '.DS_Store')

die() { printf '\033[31mREFUSED\033[0m %s\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32mOK\033[0m %s\n' "$*"; }

# A per-file digest over the WHOLE tree, not a hand-picked list. A canary grep
# for known-falsified strings only catches the conclusions someone remembered to
# add; byte equality catches every one of them, including the next.
manifest() {
  ( cd "$1" && find . -type f \
      ! -path './local/*' ! -path '*/__pycache__/*' ! -name '.DS_Store' \
      -print0 | sort -z | xargs -0 md5 -q 2>/dev/null | md5 -q )
}

verify() {
  local a b c
  a=$(manifest "$SRC"); b=$(manifest "$CODEX"); c=$(manifest "$PUB")
  if [ "$a" = "$b" ] && [ "$b" = "$c" ]; then
    ok "three copies byte-identical ($a)"
    return 0
  fi
  printf 'source  %s  %s\n' "$a" "$SRC" >&2
  printf 'codex   %s  %s\n' "$b" "$CODEX" >&2
  printf 'github  %s  %s\n' "$c" "$PUB" >&2
  echo "--- differing files ---" >&2
  diff -rq "$SRC" "$CODEX" 2>/dev/null | grep -v 'local\|__pycache__\|DS_Store' >&2
  diff -rq "$SRC" "$PUB" 2>/dev/null | grep -v 'local\|__pycache__\|DS_Store' >&2
  return 1
}

MODE=sync; MSG=""; DO_PUSH=0
while [ $# -gt 0 ]; do
  case "$1" in
    --check)  MODE=check ;;
    --commit) MODE=commit; MSG=${2:-}; shift ;;
    --push)   DO_PUSH=1 ;;
    *)        die "unknown argument: $1" ;;
  esac
  shift
done

[ -f "$SRC/SKILL.md" ] || die "source has no SKILL.md: $SRC"

if [ "$MODE" = check ]; then
  verify || die "copies diverged — run without --check to propagate"
  exit 0
fi

# Compilation gate: never propagate a source that does not import.
for f in "$SRC"/scripts/*.py; do
  python3 -m py_compile "$f" 2>/dev/null || die "does not compile: $f"
done
ok "all scripts compile"

rsync -a --delete "${EXCL[@]}" "$SRC/" "$CODEX/" || die "rsync to codex failed"
rsync -a --delete "${EXCL[@]}" "$SRC/" "$PUB/"   || die "rsync to repo failed"

# local/ is per-user calibration and must never be published.
for d in "$CODEX/local" "$PUB/local"; do
  [ -e "$d" ] && die "local/ leaked into a derived copy: $d"
done
ok "local/ not present in derived copies"

verify || die "propagation ran but copies still differ — do not commit"

[ "$MODE" = commit ] || exit 0
[ -n "$MSG" ] || die "--commit needs a message"

cd "$REPO" || die "no repo at $REPO"
# This worktree carries long-standing unrelated deletions; `git add -A` here
# would publish them. Stage the skill path and nothing else, then prove it.
git add -- "$SUBPATH" || die "git add failed"
STRAY=$(git diff --cached --name-only | grep -v "^$SUBPATH/" || true)
[ -z "$STRAY" ] || die "staged files outside $SUBPATH: $STRAY"
if git diff --cached --quiet; then ok "nothing to commit"; exit 0; fi
git diff --cached --stat
git commit -q -m "$MSG" || die "commit failed"
ok "committed: $(git log --oneline -1)"

[ "$DO_PUSH" = 1 ] || { echo "not pushed (pass --push)"; exit 0; }
git push -q origin HEAD || die "push failed"
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] \
  || die "pushed but HEAD != origin/main"
ok "pushed, HEAD == origin/main"
