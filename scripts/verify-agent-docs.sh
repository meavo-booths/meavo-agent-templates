#!/usr/bin/env bash
# Verify filled agent docs in a target repo (automated half of CHECKLIST.md).
# Usage: verify-agent-docs.sh [target-repo-root]   (defaults to cwd)
set -uo pipefail

TARGET="$(cd "${1:-.}" && pwd)"
cd "$TARGET"

PASS=0
FAIL=0
WARN=0

ok()   { echo "  ok    $1"; PASS=$((PASS+1)); }
fail() { echo "  FAIL  $1"; FAIL=$((FAIL+1)); }
warn() { echo "  warn  $1"; WARN=$((WARN+1)); }

echo "Verifying agent docs in: $TARGET"
echo ""
echo "== Files exist =="

[[ -f AGENTS.md ]] && ok "AGENTS.md" || fail "AGENTS.md missing"
[[ -f .cursor/rules/core.mdc ]] && ok ".cursor/rules/core.mdc" || fail ".cursor/rules/core.mdc missing"
[[ -f .cursorignore ]] && ok ".cursorignore" || warn ".cursorignore missing"
[[ -f CONTRIBUTING.md ]] && ok "CONTRIBUTING.md" || warn "CONTRIBUTING.md missing (note reason in PR)"
[[ -f docs/architecture.md ]] && ok "docs/architecture.md" || warn "docs/architecture.md missing (note reason in PR)"

echo ""
echo "== No placeholders left =="

DOC_FILES=()
for f in AGENTS.md CONTRIBUTING.md .cursorignore; do
  [[ -f "$f" ]] && DOC_FILES+=("$f")
done
while IFS= read -r f; do DOC_FILES+=("$f"); done < <(find .cursor/rules docs -type f \( -name '*.mdc' -o -name '*.md' \) 2>/dev/null)

LEFTOVER=$(grep -l "FILL:" "${DOC_FILES[@]}" 2>/dev/null || true)
if [[ -n "$LEFTOVER" ]]; then
  fail "FILL: placeholders remain in: $(echo "$LEFTOVER" | tr '\n' ' ')"
else
  ok "no FILL: placeholders in agent docs"
fi

echo ""
echo "== AGENTS.md quality =="

if [[ -f AGENTS.md ]]; then
  LINES=$(wc -l < AGENTS.md | tr -d ' ')
  if [[ "$LINES" -le 170 ]]; then ok "AGENTS.md is $LINES lines (target ~150)"; else warn "AGENTS.md is $LINES lines — consider trimming (target ~150)"; fi

  # Every relative path mentioned in AGENTS.md should exist on disk
  # (skip lines that are HTML comments / examples, and glob-ish paths)
  BROKEN=0
  CHECKED=0
  while IFS= read -r p; do
    p="${p##*](}"   # markdown link: keep the target, not the label
    p="${p%%,}"; p="${p%%.}"; p="${p%%:}"; p="${p%%)}"; p="${p%%]}"
    [[ "$p" == *'*'* || "$p" == *'<'* ]] && continue
    CHECKED=$((CHECKED+1))
    [[ -e "$p" ]] || { warn "path referenced in AGENTS.md not found: $p"; BROKEN=1; }
  done < <(grep -v '<!--' AGENTS.md | grep -oE '(src|docs|packages|scripts|prisma)/[][A-Za-z0-9_./()-]+' | sort -u)
  if [[ "$CHECKED" -eq 0 ]]; then
    warn "no checkable paths found in AGENTS.md — is the task table filled?"
  elif [[ "$BROKEN" -eq 0 ]]; then
    ok "all $CHECKED paths referenced in AGENTS.md exist"
  fi

  grep -qi "do not" AGENTS.md && ok "Do NOT section present" || fail "no Do NOT section in AGENTS.md"
fi

echo ""
echo "== Cursor rules =="

if [[ -f .cursor/rules/core.mdc ]]; then
  grep -q "alwaysApply: true" .cursor/rules/core.mdc && ok "core.mdc has alwaysApply: true" || fail "core.mdc missing alwaysApply: true"
fi

if [[ -f .cursorrules && -d .cursor/rules ]]; then
  RULES_LINES=$(grep -vc '^\s*#\|^\s*$' .cursorrules 2>/dev/null || echo 0)
  [[ "$RULES_LINES" -gt 2 ]] && warn ".cursorrules still has content — merge into .cursor/rules/core.mdc" || ok ".cursorrules is a pointer stub or trivial"
fi

# Glob targets in scoped rules should exist
for rule in .cursor/rules/domain.mdc .cursor/rules/api.mdc .cursor/rules/ui.mdc .cursor/rules/legacy.mdc; do
  [[ -f "$rule" ]] || continue
  while IFS= read -r g; do
    [[ "$g" == *'<'* ]] && { warn "$rule has unfilled glob placeholder"; continue; }
    base="${g%%\**}"; base="${base%/}"
    [[ -z "$base" || -e "$base" ]] || warn "$rule glob targets missing dir: $g"
  done < <(awk '/^globs:/{f=1;next} /^---/{f=0} f && /^[[:space:]]*-[[:space:]]+/{sub(/^[[:space:]]*-[[:space:]]+/,""); print; next} f && !/^[[:space:]]*-/{f=0}' "$rule")
done
ok "scoped rule glob check complete"

echo ""
echo "== Result: $PASS ok, $WARN warnings, $FAIL failures =="
[[ "$FAIL" -eq 0 ]] || exit 1
