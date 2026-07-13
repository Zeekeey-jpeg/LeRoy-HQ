#!/usr/bin/env python3
"""Regenerate memory/Projects/System-101-Training/progress.md from progress.json.
Run after every status change in progress.json (called by the daily-lesson skill,
and safe to re-run manually any time -- it is a pure read-json/write-md render, idempotent)."""
import json
from collections import OrderedDict
from datetime import date
from pathlib import Path

PROJECT_DIR = Path(r"~/.claude\memory\Projects\System-101-Training")
JSON_PATH = PROJECT_DIR / "progress.json"
MD_PATH = PROJECT_DIR / "progress.md"


def main():
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    topics = data["topics"]
    total = len(topics)
    covered = [t for t in topics if t["status"] == "covered"]
    n_covered = len(covered)
    pct = round(100 * n_covered / total, 1) if total else 0.0

    by_cat = OrderedDict()
    for t in topics:
        by_cat.setdefault(t["category"], {"covered": 0, "total": 0})
        by_cat[t["category"]]["total"] += 1
        if t["status"] == "covered":
            by_cat[t["category"]]["covered"] += 1

    last_covered = None
    for t in reversed(covered):
        if t.get("date_covered"):
            last_covered = t
            break
    next_up = next((t for t in topics if t["status"] == "not_started"), None)

    today = date.today().isoformat()

    lines = []
    lines.append("---")
    lines.append("name: System 101 Training - Progress Tracker")
    lines.append("description: Daily learning-drip progress tracker for the System 101 KB (390-topic curriculum condensed from ByteByteGo system-design-101)")
    lines.append("type: project")
    lines.append("created: 2026-07-12")
    lines.append(f"modified: {today}")
    lines.append("tags: [projects, learning, system-design]")
    lines.append("project: System 101 Training")
    lines.append("---")
    lines.append("")
    lines.append("# System 101 Training — Progress Tracker")
    lines.append("")
    lines.append("**Goal:** Learn the entire System 101 KB (`skills/domains/system-101/`) one topic")
    lines.append("at a time via an automated daily ~9am email.")
    lines.append(f"**Curriculum size:** {total} topics across {len(by_cat)} categories.")
    lines.append("**Source:** github.com/ByteByteGoHq/system-design-101 (condensed KB: `skills/domains/system-101/`)")
    lines.append("**Delivery:** Daily ~9am email to you@example.com — Windows Task Scheduler")
    lines.append("(`system101-daily-lesson`) → `skills/routines/system-101-daily-lesson.md`")
    lines.append("**Canonical state:** `memory/Projects/System-101-Training/progress.json` (this file is a")
    lines.append("generated mirror — always edit progress.json + re-run `scripts/render-system101-progress-md.py`,")
    lines.append("never hand-edit the table below).")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Quick Report Trigger")
    lines.append("")
    lines.append('When Brian asks "how far along am I", "system 101 progress", "how many topics left",')
    lines.append('or similar → read this file and report: topics covered, topics remaining, percent')
    lines.append("complete, most recent topic covered + date, and the next topic up.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Progress by Category")
    lines.append("")
    lines.append("| Category | Covered | Total |")
    lines.append("|---|---|---|")
    for cat, c in by_cat.items():
        lines.append(f"| {cat} | {c['covered']} | {c['total']} |")
    lines.append("")
    lines.append(f"**Overall Progress: {n_covered}/{total} covered ({pct}%)**")
    if last_covered:
        lines.append(f"**Last covered:** {last_covered['title']} — {last_covered['date_covered']}")
    if next_up:
        lines.append(f"**Next up:** {next_up['title']} ({next_up['category']})")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Topic Log")
    lines.append("")
    lines.append("| # | Topic | Category | Status | Date Covered |")
    lines.append("|---|---|---|---|---|")
    for t in topics:
        mark = "✅" if t["status"] == "covered" else "⬜"
        d = t["date_covered"] or "—"
        lines.append(f"| {t['id']} | {t['title']} | {t['category']} | {mark} | {d} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Tracker created: 2026-07-12 | Last updated: {today}*")
    lines.append("")

    MD_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {MD_PATH} ({n_covered}/{total} covered, {pct}%)")


if __name__ == "__main__":
    main()
