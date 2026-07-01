---
name: Session Recap Email (Branded)
description: Standard branded HTML email format for ALL client session recaps (ExampleClient, ExampleClient, ExampleClient, any client). Dynamic subject + footer per client/topic.
type: skill
created: 2026-06-19
tags: [email, client, recap, branding, template]
triggers:
  - "session recap"
  - "draft a recap"
  - "send out a recap"
  - "we just met with <client>"
  - "we're all done for the day" (in a client-session context)
---

# Session Recap Email — Standard Branded Format

This is the **default format for every client session recap** — ExampleClient, ExampleClient, ExampleClient,
and any future client. the user loves this format; use it every time unless he says otherwise.

## Hard Rules (do not violate)

1. **NEVER write "EDGE" in any client email — ever.** EDGE is internal tooling. In recaps,
   describe what was done in plain your BIM tool/workflow terms. (See [[feedback_no_edge_in_emails]].)
2. **Footer descriptor is DYNAMIC per client + engagement type.** It must reflect the actual
   service for that client — NOT a hardcoded "your BIM tool Training."
   - ExampleClient → `your BIM tool Training for ExampleClient Engineering`
   - ExampleClient → `your BIM tool Training for ExampleClient` (your BIM tool-based engagement)
   - ExampleClient (Jess Leckrone) → NOT your BIM tool. Use the real engagement (e.g. `AI Consulting for ExampleClient`).
     Never reference your BIM tool for a client we don't do your BIM tool with.
   - Rule of thumb: footer = `<Service Type> for <Client>` where Service Type = what we
     actually do with them. If unsure, ask the user rather than guess.
3. **Subject line is DYNAMIC and relevant to the actual topic.** Format:
   `<Client> <Service> — Session Recap <YYYY-MM-DD> + Next Session (<next date>)`.
   The middle should describe what the session was about, not a generic label.
4. **No white (or light) text on light backgrounds.** White text is only allowed on the
   dark navy bands (header/footer). Body = dark text (#243044) on white.
5. **Checkmarks use the numeric entity `&#10003;`** (NOT `&check;` — Gmail does not render
   the named entity and shows literal text). Calendar icon = `&#128197;`.
6. **Always park in the user's Drafts for review first** (gmail_createDraft, never auto-send).
   Use the gmail protocol — never raw send.

## Recipient Protocol (ExampleClient specifically)
- **To:** Norman, Karen, Jonathan, Keiko, Daniel @exampleclientengineers.com
- **CC:** Stephen ExampleClient (stephen@exampleclientengineers.com)
- For other clients, pull the team/CC list from that client's tracker/contact file.

## Color Palette
- Navy band: `#16243f` (white text OK here)
- Accent blue: `#2d6cdf` (section header rules, checkmarks, signature bar)
- Body text: `#243044` on white `#ffffff`
- Page background: `#eef1f5`
- Callout box (reminders): bg `#fff4e0`, left border `#e09b2d`, dark amber text `#8a5a12` / `#6b4a14`
- Muted/italic note text: `#52607a`

## Structure (sections, in order)
1. **Navy header band** — "your org" + right-aligned service tag, accent rule, "Session Recap — <date>", subtitle line (project context + time)
2. **Intro** — short warm 1–2 sentence opener
3. **What We Covered** — accent section header + checklist rows (`&#10003;` + bold lead + em-dash detail)
4. **Callout box** (when relevant) — e.g. "No session next week", holiday, schedule change
5. **Next Session** — accent section header + numbered priorities; optional italic "why/strategy" note
6. **Sign-off** — warm closing line
7. **Signature** — accent left-bar: the user / your org / you@example.com
8. **Navy footer band** — DYNAMIC descriptor: `<Service Type> for <Client>`

## Reference Implementation
The ExampleClient 2026-06-19 recap (draft id `19ee06b75710345d`) is the canonical example of this
format fully filled in. Copy its HTML as the starting skeleton, then swap:
- Header date + subtitle
- "What We Covered" rows
- Callout (or remove the row entirely if none)
- "Next Session" items + strategy note
- Subject line (dynamic)
- Footer descriptor (dynamic per client — NEVER hardcode your BIM tool)
