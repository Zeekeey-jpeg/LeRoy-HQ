# Morning CEO Email — Daily Brief Skill

**Trigger:** CronCreate Mon–Fri 9:03 AM ET (auto) | Fully autonomous | No user input needed
**Sends to:** you@example.com
**Subject:** `your org CEO Brief — {DayName}, {Month} {Day}`

---

## Execution Flow

### Step 1 — Gather Data (run in parallel)

**A. Today's Calendar**
- Tool: `mcp__email-primary__list_events`
- calendar: `you@example.com`, timeMin: today 00:00, timeMax: today 23:59, singleEvents: true, orderBy: startTime
- Extract: up to 6 events (time + title)

**B. Unread Email Count**
- Tool: `mcp__email-primary__search_mail`
- query: `is:unread in:inbox`, max_results: 1
- Extract: resultSizeEstimate or length of messages array

**C. Pipeline — your CRM**
- Tool: `mcp__crm__list_deals` (or search_deals with open filter)
- Extract: count of active deals, sum of `amount` field, top 3 by value with stage
- If unavailable: use `[offline]` — still send email

**D. Boardroom Decisions**
- Tool: `mcp__leroy__leroy_decisions`
- Extract: 3 most recent decisions (topic + 1-line outcome + date)
- If empty or all >5 days old: note "No recent boardroom session."

**E. Harness Systems Status**
Read these files and extract key fields:
- `~/.claude\daemon.status.json` → uptime, status
- `~/.claude\daemon.log` → last 5 lines (recent activity)
- `~/.claude\session\state.json` → last run times for: memory_recall, email_scan, secretary
- Infer Q3 campaign status (40/day outreach cadence — check if your org-Q3Followup task mention in recent logs)

For each system, classify as RUNNING / STALLED / OFFLINE based on last-run recency:
- RUNNING: ran within expected interval
- STALLED: overdue but not failed
- OFFLINE: no signal / file missing

**F. Smart Todos / Reminders**
- Tool: `mcp__leroy-vault__smart_todos` (or Read `~/.claude\session\reminders.json`)
- Extract: top 3 by priority, show title + due date

---

### Step 2 — Generate Growth Tip

Analyze the gathered data and write ONE specific, actionable tip. Rules:
- If any your CRM deal has `hs_lastmodifieddate` > 7 days ago AND is not closed: "Deal with [Company] has been sitting at [Stage] for [X] days. A 3-sentence check-in today could unstick it."
- If no outreach system ran in 48h: "Your outreach cadence paused. Even 5 personalized LinkedIn touches today keeps pipeline warm."
- If there's a client with recent email activity but no follow-up task: "You had recent contact with [Client] — no follow-up task exists. Add one now before it slips."
- If no deals and no outreach running: "No active pipeline movement detected. Block 20 minutes today to identify 3 warm contacts you haven't touched in 30+ days."
- If it's Monday: "Start the week with a pipeline review — identify the one deal most likely to close this month and make that your first call."
- Fallback: "your org's best growth lever right now is proof-of-value. Think of one client who had a win you haven't documented yet. A quick case study draft today pays dividends for months."

Keep to 2–3 sentences. Write as a sharp COO nudge, not a chatbot suggestion.

---

### Step 3 — Build HTML Email

Fill the template below. Replace every `{PLACEHOLDER}`. Never omit a section — use `[—]` if data unavailable.

### Gmail-Safe HTML Rules (MUST FOLLOW)
- All CSS INLINE on each element — no `<style>` blocks, no `<head>` CSS whatsoever
- Table-based layout only — no flexbox, no grid, no `<div>` as layout
- No external images, no `<img>` tags at all — use emoji as section icons
- No external fonts — `font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif` only
- No `@media` queries, no JavaScript
- Use `bgcolor` attribute AND inline `background-color` style on every colored cell (belt + suspenders)
- Max width 600px container
- Line-height on all `<p>` text
- `<p>` margins: use `margin:0 0 8px 0` not shorthand `margin:0 0 8px`

---

## HTML TEMPLATE

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>your org CEO Brief</title>
</head>
<body style="margin:0;padding:0;background-color:#eef2f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#eef2f7" style="background-color:#eef2f7;">
<tr><td align="center" style="padding:24px 12px;">

<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;">

  <!-- ═══ HEADER ═══ -->
  <tr>
    <td bgcolor="#1e293b" style="background-color:#1e293b;padding:24px 28px;border-radius:12px 12px 0 0;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="vertical-align:bottom;">
            <p style="margin:0 0 4px 0;color:#818cf8;font-size:10px;font-weight:700;letter-spacing:3px;text-transform:uppercase;">YOUR ORG &mdash; CEO BRIEFING</p>
            <p style="margin:0 0 3px 0;color:#f1f5f9;font-size:22px;font-weight:700;line-height:1.2;">{DAY_NAME}, {MONTH_DAY}</p>
            <p style="margin:0;color:#64748b;font-size:12px;">Good morning, the user.</p>
          </td>
          <td align="right" style="vertical-align:top;">
            <span style="display:inline-block;background-color:#6366f1;color:#ffffff;font-size:10px;font-weight:700;letter-spacing:1px;padding:5px 14px;border-radius:20px;">DAILY BRIEF</span>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ═══ QUICK STATS BAR ═══ -->
  <tr>
    <td bgcolor="#ffffff" style="background-color:#ffffff;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td width="25%" align="center" style="padding:16px 8px;border-right:1px solid #e2e8f0;">
            <p style="margin:0;color:#6366f1;font-size:22px;font-weight:700;line-height:1;">{DEAL_COUNT}</p>
            <p style="margin:3px 0 0 0;color:#94a3b8;font-size:10px;text-transform:uppercase;letter-spacing:1px;">Deals</p>
          </td>
          <td width="25%" align="center" style="padding:16px 8px;border-right:1px solid #e2e8f0;">
            <p style="margin:0;color:#10b981;font-size:22px;font-weight:700;line-height:1;">{PIPELINE_VALUE}</p>
            <p style="margin:3px 0 0 0;color:#94a3b8;font-size:10px;text-transform:uppercase;letter-spacing:1px;">Pipeline</p>
          </td>
          <td width="25%" align="center" style="padding:16px 8px;border-right:1px solid #e2e8f0;">
            <p style="margin:0;color:#f59e0b;font-size:22px;font-weight:700;line-height:1;">{UNREAD_COUNT}</p>
            <p style="margin:3px 0 0 0;color:#94a3b8;font-size:10px;text-transform:uppercase;letter-spacing:1px;">Unread</p>
          </td>
          <td width="25%" align="center" style="padding:16px 8px;">
            <p style="margin:0;color:#334155;font-size:22px;font-weight:700;line-height:1;">{MEETING_COUNT}</p>
            <p style="margin:3px 0 0 0;color:#94a3b8;font-size:10px;text-transform:uppercase;letter-spacing:1px;">Meetings</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ═══ SECTION: TODAY'S SCHEDULE ═══ -->
  <tr>
    <td bgcolor="#ffffff" style="background-color:#ffffff;padding:20px 28px;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;border-top:1px solid #e2e8f0;">
      <p style="margin:0 0 12px 0;color:#6366f1;font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;">&#x1F4C5; TODAY&rsquo;S SCHEDULE</p>
      {CALENDAR_CONTENT}
    </td>
  </tr>

  <!-- ═══ SECTION: PIPELINE ═══ -->
  <tr>
    <td style="padding:0;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr><td bgcolor="#6366f1" style="background-color:#6366f1;padding:8px 28px;"><p style="margin:0;color:#ffffff;font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;">&#x1F4BC; PIPELINE</p></td></tr>
        <tr><td bgcolor="#ffffff" style="background-color:#ffffff;padding:16px 28px;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">{PIPELINE_CONTENT}</td></tr>
      </table>
    </td>
  </tr>

  <!-- ═══ SECTION: BOARDROOM PULSE ═══ -->
  <tr>
    <td style="padding:0;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr><td bgcolor="#0f766e" style="background-color:#0f766e;padding:8px 28px;"><p style="margin:0;color:#ffffff;font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;">&#x1F3DB; BOARDROOM PULSE</p></td></tr>
        <tr><td bgcolor="#f0fdf9" style="background-color:#f0fdf9;padding:16px 28px;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">{BOARDROOM_CONTENT}</td></tr>
      </table>
    </td>
  </tr>

  <!-- ═══ SECTION: GROWTH TIP ═══ -->
  <tr>
    <td style="padding:0;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr><td bgcolor="#b45309" style="background-color:#b45309;padding:8px 28px;"><p style="margin:0;color:#ffffff;font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;">&#x1F4A1; TODAY&rsquo;S GROWTH TIP</p></td></tr>
        <tr><td bgcolor="#fffbeb" style="background-color:#fffbeb;padding:16px 28px;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">{GROWTH_TIP_CONTENT}</td></tr>
      </table>
    </td>
  </tr>

  <!-- ═══ SECTION: HARNESS PULSE ═══ -->
  <tr>
    <td style="padding:0;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr><td bgcolor="#1d4ed8" style="background-color:#1d4ed8;padding:8px 28px;"><p style="margin:0;color:#ffffff;font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;">&#x26A1; HARNESS PULSE</p></td></tr>
        <tr><td bgcolor="#eff6ff" style="background-color:#eff6ff;padding:16px 28px;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">{HARNESS_CONTENT}</td></tr>
      </table>
    </td>
  </tr>

  <!-- ═══ SECTION: ON YOUR PLATE ═══ -->
  <tr>
    <td style="padding:0;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr><td bgcolor="#7c3aed" style="background-color:#7c3aed;padding:8px 28px;"><p style="margin:0;color:#ffffff;font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;">&#x1F4CC; ON YOUR PLATE</p></td></tr>
        <tr><td bgcolor="#ffffff" style="background-color:#ffffff;padding:16px 28px;border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;border-bottom:1px solid #e2e8f0;">{TODOS_CONTENT}</td></tr>
      </table>
    </td>
  </tr>

  <!-- ═══ FOOTER ═══ -->
  <tr>
    <td bgcolor="#1e293b" style="background-color:#1e293b;padding:14px 28px;text-align:center;border-radius:0 0 12px 12px;">
      <p style="margin:0;color:#475569;font-size:11px;line-height:1.5;">your org CEO Brief &bull; Auto-generated {DATE_TIME_ET}<br>
      <span style="color:#334155;">you@example.com</span></p>
    </td>
  </tr>

</table>

</td></tr>
</table>
</body>
</html>
```

---

## Content Block Specs

### {CALENDAR_CONTENT}
```html
<!-- Repeat per event, max 6 -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:6px;">
  <tr>
    <td style="width:65px;color:#6366f1;font-size:12px;font-weight:600;vertical-align:top;white-space:nowrap;">{TIME}</td>
    <td style="color:#334155;font-size:13px;line-height:1.4;">{TITLE}</td>
  </tr>
</table>
```
No events fallback:
```html
<p style="margin:0;color:#94a3b8;font-size:13px;font-style:italic;">No meetings today. Good day to reach out proactively.</p>
```

### {PIPELINE_CONTENT}
```html
<p style="margin:0 0 10px 0;color:#475569;font-size:13px;">
  <strong style="color:#10b981;">{COUNT} active deals</strong> &mdash; total pipeline: <strong style="color:#10b981;">${VALUE}</strong>
</p>
<!-- Top 3 deals -->
<table role="presentation" width="100%" cellpadding="3" cellspacing="0" border="0">
  <tr>
    <td style="color:#334155;font-size:12px;">{COMPANY}</td>
    <td style="color:#6366f1;font-size:12px;font-weight:600;text-align:right;white-space:nowrap;">${AMOUNT}</td>
    <td style="color:#94a3b8;font-size:11px;text-align:right;padding-left:8px;white-space:nowrap;">{STAGE}</td>
  </tr>
</table>
```
If stage changes in last 24h, add:
```html
<p style="margin:10px 0 0 0;color:#f59e0b;font-size:12px;">&#x26A0; Stage change: {COMPANY} moved to {NEW_STAGE}</p>
```
Unavailable fallback:
```html
<p style="margin:0;color:#94a3b8;font-size:13px;">[your CRM offline &mdash; check connection]</p>
```

### {BOARDROOM_CONTENT}
```html
<p style="margin:0 0 10px 0;color:#64748b;font-size:11px;">Last session: {DATE}</p>
<!-- Repeat per decision, max 3 -->
<p style="margin:0 0 8px 0;">
  <span style="color:#0f766e;font-weight:700;">&#x25B8;</span>
  <span style="color:#334155;font-size:13px;line-height:1.5;"> {DECISION_SUMMARY}</span>
</p>
<!-- If action items exist -->
<p style="margin:10px 0 0 0;color:#64748b;font-size:11px;font-style:italic;">&#x1F4CB; Action items in Leroy triage &mdash; check before EOD.</p>
```
No session fallback:
```html
<p style="margin:0;color:#94a3b8;font-size:13px;font-style:italic;">No boardroom session in the last 5 days.</p>
```

### {GROWTH_TIP_CONTENT}
```html
<p style="margin:0 0 6px 0;color:#92400e;font-size:13px;font-weight:700;">{TIP_HEADLINE}</p>
<p style="margin:0;color:#78350f;font-size:13px;line-height:1.6;">{TIP_BODY_2_TO_3_SENTENCES}</p>
```

### {HARNESS_CONTENT}
Badge colors: RUNNING=`#dcfce7`/`#166534` | STALLED=`#fef3c7`/`#92400e` | OFFLINE=`#fee2e2`/`#991b1b`
```html
<table role="presentation" width="100%" cellpadding="4" cellspacing="0" border="0">
  <!-- Repeat per system -->
  <tr>
    <td style="color:#334155;font-size:12px;width:45%;">{SYSTEM_NAME}</td>
    <td style="width:70px;">
      <span style="display:inline-block;background-color:{BADGE_BG};color:{BADGE_TEXT};font-size:9px;font-weight:700;padding:2px 8px;border-radius:10px;letter-spacing:0.5px;">{STATUS}</span>
    </td>
    <td style="color:#94a3b8;font-size:11px;text-align:right;">{DETAIL}</td>
  </tr>
</table>
```

Systems to check (in order):
1. Daemon / Monitor System
2. Q3 Outreach Campaign (40/day cadence)
3. a lead-gen module (geo + API status)
4. Memory Recall
5. Leroy Boardroom

### {TODOS_CONTENT}
```html
<table role="presentation" width="100%" cellpadding="4" cellspacing="0" border="0">
  <!-- Repeat per item, max 3 -->
  <tr>
    <td style="width:16px;color:#7c3aed;font-size:12px;vertical-align:top;">&#x25B8;</td>
    <td style="color:#334155;font-size:13px;line-height:1.4;">
      {TITLE} <span style="color:#94a3b8;font-size:11px;">({PRIORITY} &middot; {DUE_DATE})</span>
    </td>
  </tr>
</table>
```
Empty fallback:
```html
<p style="margin:0;color:#94a3b8;font-size:13px;font-style:italic;">Plate is clear. Good time to get ahead.</p>
```

---

### Step 4 — Send Email

Call: `mcp__email-primary__send_mail`
```json
{
  "to": "you@example.com",
  "subject": "your org CEO Brief — {DAY_NAME}, {MONTH_DAY}",
  "body": "{FULL_HTML_STRING}"
}
```

If the tool uses separate `body_html` vs `body` parameters, pass HTML in `body_html` and a plain-text fallback in `body`.

**On send failure:** Append to `~/.claude\daemon.log`:
```
[MORNING-EMAIL-ERROR] {timestamp} Failed to send CEO brief: {error}
```

---

## Failure Modes

| Problem | Action |
|---------|--------|
| your CRM offline | Show `[offline]`, continue |
| Calendar auth failure | Show "Calendar unavailable", continue |
| No boardroom decisions file | Show "No recent session", continue |
| send_mail fails | Log to daemon.log, do not retry |
| Leroy MCP offline | Read files directly as fallback |
