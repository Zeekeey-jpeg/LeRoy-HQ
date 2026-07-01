#!/usr/bin/env python3
"""
File Organization Enforcer v1.0
Prevents file dumping in the wrong locations under ~/.claude.
Can be called by the gate/write path for every file write.

Generic rules (customize the sets/patterns below for your own layout):
  - Scripts (.py/.ps1/.sh) must live under scripts/, not at the root.
  - Data files (.csv, non-config .json) must live under data/.
  - Reports (.html, *-report.md) must live under reports/.
  - Temp files must live under temp/.
  - session/ sub-buckets: investigations/, drafts/, cache/ for matching files.

Returns (is_valid, error_message) from validate_file_path(); a suggested target
from suggest_correct_path().
"""

import os
import re
from pathlib import Path

CLAUDE_ROOT = Path.home() / ".claude"
SESSION = CLAUDE_ROOT / "session"

# Config files allowed at the .claude root. Extend for your own root config.
ROOT_CONFIG_FILES = {
    "CLAUDE.md", "SOUL.md", "USER.md", "IDENTITY.md",
    "settings.json", "settings.local.json", "history.jsonl",
    ".gitignore", "README.md",
}

# Core files allowed at the session root (not in a sub-bucket).
SESSION_CORE_FILES = {
    "state.json", "state-cold.json", "state-hot.json",
    "metrics.json", "enforcement.todo", "prompt-history.jsonl",
    "context-anchor.md", "error-log.jsonl",
}


def is_root_level(path_str: str) -> bool:
    """Check if file is at .claude root (not in a subfolder)"""
    path = Path(path_str)
    try:
        relative = path.relative_to(CLAUDE_ROOT)
        return '/' not in str(relative) and '\\' not in str(relative)
    except ValueError:
        return False


def is_session_root(path_str: str) -> bool:
    """Check if file is at session root (not in a subfolder)"""
    path = Path(path_str)
    try:
        relative = path.relative_to(SESSION)
        return '/' not in str(relative) and '\\' not in str(relative)
    except ValueError:
        return False


def matches_investigation_pattern(filename: str) -> bool:
    """Check if filename matches investigation/debug patterns"""
    patterns = [
        r'.*POSTMORTEM.*\.md$',
        r'.*-investigation\.md$',
        r'.*-error-.*\.md$',
        r'^COMPLETION-.*\.txt$',
        r'.*-repair-log\.md$',
    ]
    return any(re.match(p, filename, re.IGNORECASE) for p in patterns)


def matches_draft_pattern(filename: str) -> bool:
    """Check if filename matches draft patterns"""
    patterns = [
        r'.*-draft.*\.html$',
        r'.*-draft.*\.md$',
        r'.*-snippet\.txt$',
    ]
    return any(re.match(p, filename, re.IGNORECASE) for p in patterns)


def validate_file_path(path_str: str) -> tuple[bool, str]:
    """
    Validate file path against organization rules.
    Returns: (is_valid, error_message)
    """
    path = Path(path_str)
    filename = path.name

    # Skip validation for paths outside .claude
    if not str(path).startswith(str(CLAUDE_ROOT)):
        return True, ""

    # Rule 1: No scripts in .claude root
    if path.suffix in ['.py', '.ps1', '.sh']:
        if is_root_level(path_str):
            return False, f"Scripts must go in scripts/ directory: {filename}"

    # Rule 2: No data files in .claude root (except config)
    if path.suffix in ['.csv'] or (path.suffix == '.json' and filename not in ROOT_CONFIG_FILES):
        if is_root_level(path_str):
            if filename not in ROOT_CONFIG_FILES and not filename.startswith('.'):
                return False, f"Data files must go in data/ directory: {filename}"

    # Rule 3: No reports in .claude root
    if path.suffix == '.html' or filename.endswith('-report.md'):
        if is_root_level(path_str):
            return False, f"Reports must go in reports/ directory: {filename}"

    # Rule 4: Temp files with 'temp' in name go to temp/
    if 'temp' in filename.lower() and not str(path).endswith('temp/'):
        if is_root_level(path_str):
            return False, f"Temporary files must go in temp/ directory: {filename}"

    # Rule 5: Investigation/debug files go to session/investigations/
    if 'session' in str(path) and matches_investigation_pattern(filename):
        if '/investigations/' not in str(path) and '\\investigations\\' not in str(path):
            if is_session_root(path_str):
                return False, f"Investigation files must go in session/investigations/: {filename}"

    # Rule 6: Draft files go to session/drafts/
    if 'session' in str(path) and matches_draft_pattern(filename):
        if '/drafts/' not in str(path) and '\\drafts\\' not in str(path):
            if is_session_root(path_str):
                return False, f"Draft files must go in session/drafts/: {filename}"

    # Rule 7: Large cache files go to session/cache/
    if 'session' in str(path) and filename in ['memory-graph.json', 'memory-index.json']:
        if '/cache/' not in str(path) and '\\cache\\' not in str(path):
            return False, f"Large cache files must go in session/cache/: {filename}"

    # Rule 8: Prevent path corruption (malformed directory names)
    if re.search(r'[A-Za-z]:Users[^\\]', str(path)):
        return False, f"Malformed path detected (missing backslashes): {path}"

    return True, ""


def suggest_correct_path(path_str: str) -> str:
    """Suggest the correct path for a misplaced file"""
    path = Path(path_str)
    filename = path.name

    # Scripts
    if path.suffix in ['.py', '.ps1', '.sh']:
        return str(CLAUDE_ROOT / "scripts" / filename)

    # Data files
    if path.suffix == '.csv':
        return str(CLAUDE_ROOT / "data" / filename)

    # Reports
    if path.suffix == '.html' or filename.endswith('-report.md'):
        return str(CLAUDE_ROOT / "reports" / filename)

    # Temp files
    if 'temp' in filename.lower():
        return str(CLAUDE_ROOT / "temp" / filename)

    # Session files
    if 'session' in str(path):
        if matches_investigation_pattern(filename):
            return str(SESSION / "investigations" / filename)
        if matches_draft_pattern(filename):
            return str(SESSION / "drafts" / filename)
        if filename in ['memory-graph.json', 'memory-index.json']:
            return str(SESSION / "cache" / filename)

    return path_str  # No suggestion


if __name__ == "__main__":
    # Self-test with generic example paths
    root = str(CLAUDE_ROOT).replace("\\", "/")
    test_files = [
        f"{root}/test_script.py",
        f"{root}/data_file.csv",
        f"{root}/session/error-investigation.md",
        f"{root}/session/email-draft.html",
        f"{root}/session/memory-graph.json",
    ]

    for file in test_files:
        valid, msg = validate_file_path(file)
        if not valid:
            suggestion = suggest_correct_path(file)
            print(f"[X] {msg}")
            print(f"    Suggested: {suggestion}")
        else:
            print(f"[OK] {file}")
