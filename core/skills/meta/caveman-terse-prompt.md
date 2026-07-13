# Caveman Terse-Prompt Compression

*Protocol for compressing verbose prompts/instructions into maximally terse form while preserving 100% semantic content.*

---

## WHEN TO USE

- Token-budget pressure (approaching context limit)
- Prompt distillation before handoff to smaller/cheaper model
- Condensing verbose skill docs before embedding in another prompt
- Any time instruction text needs to shrink without losing meaning

---

## INPUT/OUTPUT Contract

**Input:** A prompt or skill markdown file — either a file path (e.g. `~/.claude\skills\meta\some-skill.md`) or pasted text passed directly.

**Output:** The same content rewritten in caveman-terse form per the 5 Rules below.

- If invoked as a file transform (input = path), write the compressed result back to the same file, in place.
- If invoked with pasted text (input = inline text, no path), return the compressed result inline in the response — do not create a new file.

**Determinism requirement (non-negotiable):** This transform must be deterministic and repeatable — same input + same 5 Rules => same output, every time. No creative rewriting, no rephrasing beyond what the rules specify, no dropping or altering protected tokens (see Rule 5 / WHAT NEVER TO TOUCH below). If two runs on identical input would plausibly diverge, the compression was under-specified — fall back to the more conservative (less-compressed) form.

---

## The 5 Rules

### 1. Drop articles/filler words

Remove words that don't change meaning: "a", "an", "the", "please", "kindly", "just", "simply", "in order to", "so that", "basically", "really", "actually", "very", "that" (as filler).

| Before | After |
|--------|-------|
| "Please just simply check the file in order to see if it exists" | "Check file exists" |

### 2. Collapse markdown headers into inline tags

Turn `## Section Name` into bracketed inline tag `[SECTION NAME]` or `SECTION:` prefix. Structure survives without header syntax overhead.

| Before | After |
|--------|-------|
| `## Error Handling\n\nWhen an error occurs...` | `[ERROR HANDLING] When error occurs...` |

### 3. Replace verbose instructions with imperative fragments

Turn full sentences into terse imperative commands. Drop subject, drop hedging, keep the verb + object.

| Before | After |
|--------|-------|
| "You should make sure to check whether X is true before doing Y" | "Check X before Y" |
| "It is important that you validate the input before processing it" | "Validate input before processing" |

### 4. Strip repeated boilerplate

Identify disclaimers/preambles/reminders duplicated across a prompt. State once, reference thereafter (e.g. "see above" or omit on repeat).

| Before | After |
|--------|-------|
| "Never commit without review... [later] ...remember, never commit without review... [later] ...as stated, never commit without review" | "Never commit without review" (stated once, first occurrence only) |

### 5. Zero semantic-loss guardrail (non-negotiable, overrides rules 1-4)

Keep VERBATIM, byte-for-byte — never paraphrase, abbreviate, or touch:

- Proper nouns (names, product names, agent names)
- File paths / directory paths
- Code identifiers (function names, variables, class names)
- CLI flags / command syntax
- Keyword routing triggers (hot-list phrases like "backup", "morning briefing")
- URLs
- Quoted literal strings
- Numbers, dates, versions, flags

If compression would touch any protected token, skip compression on that token and compress only the surrounding filler.

---

## WHAT NEVER TO TOUCH

| Class | Example |
|-------|---------|
| Proper nouns | `YourCo`, `Brian`, `Fable`, `Sonnet` |
| File/dir paths | `~/.claude\skills\meta\` |
| Code identifiers | `supabase_select`, `POLL_SEC`, `hq-last-sync` |
| CLI flags | `--force`, `-uall`, `--no-verify` |
| Keyword routing triggers | `"backup"`, `"morning briefing"`, `"BIM tool check"` |
| URLs | `https://your-host.example` |
| Quoted literal strings | `"[LEROY-AUTO]"` |
| Numbers/dates/versions | `v5.0`, `2026-07-02`, `4PM`, `<200ms` |

---

## Worked Examples

### Example 1

**Before (verbose):**

> Please make sure that before you commit any changes to the repository, you kindly run the guardian agent so that it can review the staged files. It is important that this happens every single time, without exception, prior to running `git commit -m "message"` in the `~/.claude\` directory. Basically, never skip this step.

**After (caveman-terse):**

> [PRE-COMMIT] Run guardian, review staged files, before `git commit -m "message"` in `~/.claude\`. Never skip.

Protected tokens preserved untouched: `git commit -m "message"`, `~/.claude\`, `guardian`.

### Example 2

**Before (verbose):**

> ## Backup Procedure
>
> Whenever you are about to run a backup, it is important that you please make sure to first check that the destination drive is actually mounted. You should basically just run the script located at `~/.claude\scripts\backup.ps1` with the `--verify` flag so that it can confirm integrity before writing anything. Please note: never skip verification before a backup. This cannot be stressed enough — never skip verification before a backup, every single time, without exception.

**After (caveman-terse):**

> [BACKUP PROCEDURE] Before backup: check destination drive mounted. Run `~/.claude\scripts\backup.ps1` with `--verify` flag, confirm integrity before writing. Never skip verification before backup.

Protected tokens preserved untouched: `~/.claude\scripts\backup.ps1`, `--verify`. (Exercises Rule 2 — header collapsed to `[BACKUP PROCEDURE]`; Rule 3 — imperative fragments; Rule 4 — repeated disclaimer stated once; Rule 5 — path + CLI flag untouched.)

### Example 3

**Before (verbose):**

> When you are setting up the integration, you will need to go to the endpoint at `https://api.YourCo.com/v2/webhooks` and register the callback there. Please be aware that this only works with version `2.3.1` of the client library or later — earlier versions will fail silently. Also, it is very important that you enter the exact string `"webhook-ready"` as the status value, because the server is basically just checking for that literal text and anything else will be rejected.

**After (caveman-terse):**

> Register callback at `https://api.YourCo.com/v2/webhooks`. Requires client library `2.3.1`+ (earlier versions fail silently). Status value must be exact string `"webhook-ready"` — anything else rejected.

Protected tokens preserved untouched: `https://api.YourCo.com/v2/webhooks`, `2.3.1`, `"webhook-ready"`. (Exercises Rule 1 — filler dropped; Rule 3 — imperative fragments; Rule 5 — URL/version/quoted-string classes untouched.)

---

## Compression Checklist

1. Scan for protected token classes first — mark them off-limits
2. Apply rules 1-4 to everything else
3. Re-read compressed output against original — confirm no semantic loss
4. If any ambiguity introduced, back off compression on that clause
