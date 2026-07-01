#!/usr/bin/env bash
# install.sh — register the leroy-boardroom module as OPT-IN (default OFF).
#
# This script only RECORDS the module and marks it disabled. It generates no
# scenes, spends no tokens, and makes no network calls. The Boardroom does
# nothing until you explicitly enable it:
#
#     leroy enable boardroom      # start convening
#     leroy disable boardroom     # pause (or create the kill-switch flag below)
#
# The Boardroom is TOKEN-HEAVY (every scene is a full model call). A flat-rate
# plan (e.g. Claude Max) is recommended over metered API billing.
set -euo pipefail

MODULE="boardroom"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
MODULES_DIR="$CLAUDE_HOME/modules"
STATE_DIR="$CLAUDE_HOME/state/boardroom"
REGISTRY="$CLAUDE_HOME/modules.json"
KILL_SWITCH="$STATE_DIR/boardroom.disabled"

mkdir -p "$MODULES_DIR" "$STATE_DIR"

# Copy the module into ~/.claude/modules/boardroom (idempotent).
DEST_DIR="$MODULES_DIR/$MODULE"
mkdir -p "$DEST_DIR"
cp -R "$SRC_DIR/." "$DEST_DIR/"

# Record enablement = false in a simple JSON registry (default OFF).
if [ ! -f "$REGISTRY" ]; then
  printf '{"modules":{}}\n' > "$REGISTRY"
fi
python3 - "$REGISTRY" "$MODULE" <<'PY' 2>/dev/null || node -e '
  const fs=require("fs"),[,,f,m]=process.argv;
  const r=JSON.parse(fs.readFileSync(f,"utf8"));
  r.modules=r.modules||{};
  r.modules[m]={enabled:false,installed_at:new Date().toISOString(),token_heavy:true};
  fs.writeFileSync(f,JSON.stringify(r,null,2)+"\n");
' "$REGISTRY" "$MODULE"
import json, sys, datetime
f, m = sys.argv[1], sys.argv[2]
r = json.load(open(f))
r.setdefault("modules", {})[m] = {
    "enabled": False,
    "installed_at": datetime.datetime.utcnow().isoformat() + "Z",
    "token_heavy": True,
}
json.dump(r, open(f, "w"), indent=2)
open(f, "a").write("\n")
PY

# Ensure the kill switch is present until the user opts in. Enabling removes it.
: > "$KILL_SWITCH"

cat <<EOF

leroy-boardroom installed — DISABLED (opt-in, token-heavy).

  Enable:   leroy enable boardroom
  Disable:  leroy disable boardroom
  Kill now: touch "$KILL_SWITCH"

  Registry: $REGISTRY
  State:    $STATE_DIR
  Config:   $DEST_DIR/config/

Recommended on a flat-rate plan (e.g. Claude Max). Nothing runs until enabled.
EOF
