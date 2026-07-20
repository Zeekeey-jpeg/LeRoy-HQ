---
name: boardroom-welcome
description: |
  Deliver the Board's first-activation welcome briefing when the user follows up
  on the "🏛️ Welcome to the Board" notification, or asks anything like "what does
  the Boardroom do" / "how often does it run" / "make it run less/more" shortly
  after turning it on for the first time.
triggers:
  - "welcome to the board"
  - "what does the boardroom do"
  - "how often does the board"
  - "board room"
---

# Boardroom welcome briefing

Fires once, the first time the user flips Boardroom on from the panel
(`POST /flow/boardroom/config {"enabled": true}` — `handlers/boardroom.py`'s
`_maybe_emit_welcome`). The backend never creates or writes into a chat session
directly (Boardroom's own rule, see `_claim_session_slot`'s docstring) — it only
posts a notification. This skill is what turns the user tapping/replying to that
notification into an actual conversation, and it never re-fires after the one
real conversation happens (`governor.json`'s `welcomed` flag guards the
notification; treat a second ask about "what does the board do" as a normal
question, not a repeat of this full briefing).

## What to say (plain language, not a wall of text)

1. **What it is.** A simulated leadership team that meets on its own to talk
   over how you've been working and suggest improvements — not autonomous
   engineering-on-its-own, more like a standing advisor that occasionally has
   ideas worth a second look.
2. **How often.** Read `~/.claude/session/boardroom/governor.json`'s
   `schedule_hours_local` (defaults to `[2, 6, 10, 14, 18, 22]` — every 4 hours)
   and say it in plain terms ("about every 4 hours"), plus the ceilings exist
   purely as a runaway-cost backstop, not the actual cadence.
3. **What it watches.** Your work patterns and how you've been using LeRoy —
   not the content of private conversations. Be direct about this; don't
   undersell it.
4. **What happens with its ideas.** A decision it proposes needs your approval
   or denial (never builds unattended). Approved decisions land in Triage as a
   startable card — nothing builds until you tap Start there. You can also open
   Triage directly any time you want a multi-step build without waiting on the
   Board to suggest one first.

## If they want to change the cadence

If they say anything like "run it less often" / "too chatty" / "more often is
fine" / "quiet hours at night":
- Translate it into concrete values — e.g. "less often" → drop
  `schedule_hours_local` to 3-4 entries spread through the day, or lower
  `max_scenes_per_day`. Use judgment on specifics; confirm what you're about to
  set in plain terms before writing it.
- Apply it via `POST /flow/boardroom/config` with `schedule_hours_local` and/or
  `max_scenes_per_day` — do not hand-edit `governor.json` directly, the merge
  logic in that endpoint preserves other fields.
- Also save it as a real preference, not just a config value: write a
  `Feedback/` note (see the Feedback memory-type convention) — subject like
  "Boardroom cadence preference", the stated preference, **Why:** in the
  user's own words, **How to apply:** the concrete schedule now in effect. This
  is what makes the choice durable across a future `leroy update` or governor
  reset, not just a value sitting in one JSON file.

## Tone

This is the ONE moment Boardroom talks about itself at length — keep it that
way. Don't repeat this briefing on later boardroom-related questions; answer
those normally and briefly instead.
