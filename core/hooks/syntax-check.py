#!/usr/bin/env python3
"""
syntax-check.py v1.0 — PostToolUse hook for Python file validation
Project-agnostic: works on any .py file anywhere on the system.

Triggered: After Edit or Write tool use
Input: JSON on stdin with tool_input containing file_path or path
Output: exits 0 (pass), exits 2 (syntax error — blocks continuation)

Performance: <50ms for most files
"""

import json
import sys
import io
import subprocess

# Force UTF-8 encoding for stdin
if sys.stdin.encoding != 'utf-8':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')


def main():
    # Read hook input from stdin
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, Exception):
        sys.exit(0)  # Can't parse input — don't block

    # Extract file path from tool_input (Edit or Write tool)
    tool_input = data.get("tool_input", {})
    file_path = (
        tool_input.get("file_path")
        or tool_input.get("path")
        or data.get("file_path")
        or ""
    )

    if not file_path:
        sys.exit(0)

    # JSON files: validate parseability — a malformed write to a config/state
    # store is a whole outage class; catch it at the write, not at the next
    # crashed reader.
    if file_path.endswith(".json"):
        try:
            with open(file_path, encoding="utf-8") as f:
                json.load(f)
        except FileNotFoundError:
            sys.exit(0)
        except json.JSONDecodeError as exc:
            print(f"\n[JSON ERROR] {file_path}")
            print(f"{exc}")
            print("Fix the malformed JSON before continuing.\n")
            sys.exit(2)
        sys.exit(0)

    # Only syntax-check Python beyond this point
    if not file_path.endswith(".py"):
        sys.exit(0)

    # Run py_compile to check syntax. Keeping this on the default hook chain
    # means child `claude -p` runs inherit it too (e.g. a curly-quote / encoding
    # corruption of a .py file is caught at write time).
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", file_path],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        # Syntax error — print structured error and exit 2 to block
        error_msg = result.stderr.strip() if result.stderr else "Unknown syntax error"
        print(f"\n[SYNTAX ERROR] {file_path}")
        print(f"{error_msg}")
        print(f"Fix the syntax error before continuing.\n")
        sys.exit(2)

    # Syntax OK — silent pass (don't spam output on every successful edit)
    sys.exit(0)


if __name__ == "__main__":
    main()
