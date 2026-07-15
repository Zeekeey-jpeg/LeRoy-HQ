<!-- ============================================================= -->
<!--  LEROY-HQ — README                                            -->
<!--  A self-growing AI company that runs in your terminal.        -->
<!-- ============================================================= -->

<p align="center">
  <img src="docs/hero.gif" alt="LeRoy — Learning Engine for Real-time Optimization & Yield" width="820" />
</p>

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=600&size=22&pause=1000&color=2D6CDF&center=true&vCenter=true&width=780&lines=A+self-growing+AI+company+that+runs+in+your+terminal.;An+org+chart+of+agents.+One+shared+memory.;It+learns+how+you+work+and+gets+better+every+day." alt="typing" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/interface-CLI%20first-080a0d?style=for-the-badge&logo=gnubash&logoColor=white" />
  <img src="https://img.shields.io/badge/platform-Windows-0078d6?style=for-the-badge&logo=windows&logoColor=white" />
  <img src="https://img.shields.io/badge/status-alpha-e09b2d?style=for-the-badge" />
  <img src="https://img.shields.io/badge/built%20on-Claude%20Code-2d6cdf?style=for-the-badge" />
  <img src="https://img.shields.io/badge/memory-Obsidian%20native-8a5cf6?style=for-the-badge" />
  <img src="https://img.shields.io/badge/license-MIT-16243f?style=for-the-badge" />
  <img src="https://img.shields.io/github/stars/Zeekeey-jpeg/LeRoy-HQ?style=for-the-badge&color=2d6cdf" />
</p>

<p align="center">
  <a href="#-choose-your-path">Install</a> ·
  <a href="#-the-org-chart--27-agents-5-tiers">Architecture</a> ·
  <a href="docs/">Docs</a> ·
  <a href="#-recent-updates">Recent Updates</a>
</p>

---

## 📰 Recent Updates

*A living log so you can see the system is actively growing, not a one-time drop.*

**2026-07-15 — Smart Todos gained a backstory layer**
The built-in todo skill now supports an optional second layer per task: a linked paper-trail
file (who asked, correspondence history, decisions, what's left) for the items worth
remembering the "why" on weeks later — while everyday items stay a one-line row. Paired with
an explicit memory-push-and-verify step, so a written note is actually retrievable later, not
just sitting on disk unindexed. See [`skills/routines/smart-todos.md`](skills/routines/smart-todos.md).

---

## What is LeRoy, actually?

LeRoy is an **AI orchestration layer** that turns Claude Code into a usable AI division —
a whole organization of specialists sharing one memory, instead of a chat window that
forgets you the moment the session ends.

Think about hiring a real team: the first few months are the expensive part, while they
learn how you like things done. **LeRoy is that team already past onboarding** — installed
in about 15 minutes, it gives you a chief-of-staff who routes what you throw at it,
specialists who do the work, and a memory that never resets.

### 🤔 Why would you actually download this?

Every Claude Code session normally starts from zero — you re-explain context, re-paste
files, re-teach it your preferences, every time. LeRoy remembers permanently, across every
session, and skips the months of work (org chart, routing, memory, guardrails) that building
this yourself would take.

### 🎯 What does it actually do for you?

| You say... | ...LeRoy does this | ...so you get |
|---|---|---|
| "Draft the follow-up to yesterday's proposal" | Routes it to the right specialist, recalls the actual thread from memory, writes it in your voice | A finished draft, not a blank page — no re-explaining the deal |
| "Should we take this deal / hire / feature on?" | Convenes a debate between five perspectives (act-now, long-view, what-breaks, people, structure) and logs a verdict | A real decision with the reasoning saved — not a vibe you'll forget you had |

### 🆚 Why this instead of just using Claude Code as-is?

Vanilla Claude Code is a capable employee with amnesia — sharp in the room, forgets you the
moment the session ends. LeRoy is the organization built around that employee: the memory,
the division of labor, the guardrails — the stuff a real company builds over months,
pre-built and running in 15 minutes. **That's the whole pitch.**

<p align="right"><i>Curious how it actually works under the hood — the agents, the memory,
the guardrails? Keep reading below.</i></p>

---

## 🚦 Choose your path

### 🌱 New here (never touched a terminal — that's totally fine)
You'll be talking to your AI company in about 15 minutes. No coding required.

### 🌟 About to install? Scroll up and hit **Star** first — one click, and it helps other people stumble onto this the way you just did.

1. Press **Start**.
2. Type **PowerShell**.
3. Hit **Enter**. The window that opens is your terminal (your **CLI**).
4. Paste this in there and hit **Enter**:
   ```powershell
   irm https://raw.githubusercontent.com/Zeekeey-jpeg/LeRoy-HQ/main/install.ps1 | iex
   ```
5. Follow the prompts.
6. **BAM — that's it.**

The installer handles everything, puts a **Leroy CLI** shortcut on your Desktop, and launches
your first session. Onboarding starts on its own — LeRoy asks a few questions about you and
your work, and builds your memory as you answer.

**From here on, you don't run any commands — you use your shortcut.** Double-click
**Leroy CLI** whenever you want to talk to LeRoy again.

Stuck at any point? Type **`leroy doctor`** — it checks everything and tells you, in plain
English, exactly how to fix whatever's missing. **`leroy reset`** undoes the whole install.

### 🔁 Already using Claude Code / comfortable in a terminal
Adopt LeRoy without losing your existing setup:
```powershell
git clone https://github.com/Zeekeey-jpeg/LeRoy-HQ "$HOME\LeRoy-HQ"
cd "$HOME\LeRoy-HQ"
.\setup.ps1
```
If you already have Claude Code content in `~/.claude`, setup backs it up automatically and
merges LeRoy in additively — nothing of yours gets overwritten.

```bash
leroy add boardroom     # optional modules, add anytime
```

**Requires:** a Claude subscription (heavy/autonomous use → Max tier). Node 18+, Python 3.11+,
and git — `leroy doctor` verifies all of this for you. **Windows-only today**; macOS/Linux
are on the roadmap, not shipped.

**Recommended model:** **Claude Sonnet** — the best balance of speed, cost, and capability
for day-to-day LeRoy use. Switch anytime in Claude Code (`/model`); the boardroom can still
pin high-stakes calls to a top-tier model when it matters.

**No login, no account needed — LeRoy runs entirely on your machine.** There's no cloud
service and nothing to sign into: it's local-to-local by design, and you talk to it through
the CLI. If you ever expose anything beyond your own machine (e.g. Tailscale Funnel), read
the warning in `AUTH-SETUP.md` first — it is not designed for open internet exposure.

---

### By the numbers
**27** agents across **5** governed tiers · **1,063** gate checks at **100%** compliance ·
warm recall **3251ms → 1622ms** · A2A mesh **2–10×** speedup · memory is **100% yours**,
plain markdown on your disk.

---

## 🏆 Why this isn't "another pile of agents"

Anyone can drop 30 agent prompts in a folder — that's the slop. LeRoy is a **system with a
control plane.** A couple of the differences that actually matter:

| Everyone has… | **LeRoy has instead…** |
|---|---|
| A bag of agents you wire yourself | A **governed org chart** — one router, 5 tiers, enforced tool-access |
| A vector store you dump text into | A memory that **forgets the right things** (confidence decay) |

**The tell for a technical reader:** LeRoy is *deterministic* (a mandatory gate guarantees
recall + routing every turn), *governed* (agents have a tool-access matrix — the C-suite
literally can't write to disk), and *self-repairing* (a tiered auto-fix engine edits code in
isolated git worktrees and rolls back on failure). Every safety rail traces to a real past
incident. That's an operating system, not a prompt dump.

---

## 🔬 A reasoning layer on top of the model

LeRoy adds a second layer of **algorithmic instinct** on top of the model — before it closes
a fix, it asks *is this isolated or systemic, and does the fix cover every instance of the
problem, not just the one you named?* It fixes the *class* of problem, not just the instance
in front of it.

## 🧠 Agents that compound — and a COO that connects the dots

Every agent keeps its **own journal** and learns as it works. That memory **persists across
sessions**, so a fresh spawn is briefed with its own history instead of starting cold — the
team gets sharper the more you use it.

And the COO holds the **30,000-foot view**. When one agent changes something in its domain, the
COO works out *who else is affected* — a change to a client record means the legal and finance
agents should know — and routes that awareness automatically (the **IMPACT protocol**).
Cross-agent impact is caught at the one place that sees every agent's output, then written to a
growing per-agent memory. One hand always knows what the other is doing.

---

## 🔓 Autonomy is opt-in (the working car)

LeRoy ships **fully capable** — but it doesn't do anything autonomous until you say yes.
Think of it like a car delivered with the engine running and the doors unlocked: the *good,
non-token-burning* features are **on by default**, and the *token-burning / self-driving*
features are **off** until you turn each one on. Nothing runs on a timer, watches your inbox,
or spends tokens in the background unless you explicitly enable it.

The autonomous features are enabled **à la carte** — during onboarding, or later, one at a
time:

```bash
leroy enable <feature>     # e.g. leroy enable boardroom
```

| On by default (safe, no background spend) | Opt-in (autonomous / uses tokens) |
|---|---|
| Self-growing memory (capture + recall) | Boardroom (24/7 debates) |
| Self-heal in **observe** mode | Morning briefing |
| The deterministic gate | Email digests |
| Request routing | Scheduled crons |
| MCP-builder (build connectors on ask) | |

**Bottom line:** everything that makes LeRoy smart works out of the box; everything that runs
*without you in the loop* stays dark until you flip it on.

---

## 🧭 The org chart — 27 agents, 5 tiers

Every request enters one front door (the **COO**). It sizes the job and answers, delegates,
or deploys a team. Agents also talk **peer-to-peer** (A2A mesh — DELEGATE / SUBSCRIBE / CACHE,
with hop limits + circuit breakers) for 2–10× speedup on big jobs. LeRoy scales the crew to
the *shape* of the work — see [docs/scaling.md](docs/scaling.md).

```mermaid
flowchart TD
    COO["🧭 COO — one front door"]

    COO --> T1
    subgraph T1["Tier 1 · Executive — govern only"]
        direction LR
        CTO["CTO"]
        CFO["CFO"]
        CKO["CKO"]
    end

    T1 --> T2
    subgraph T2["Tier 2 · Leadership"]
        direction LR
        VPE["VP-Eng"]
        HR["HR"]
    end

    T2 --> T3
    subgraph T3["Tier 3 · Management"]
        direction LR
        COS["Chief-of-Staff"]
        SCR["Scrum"]
        TL["Tech-Lead"]
        SEC["Secretary"]
    end

    T3 --> T4
    subgraph T4["Tier 4 · Specialists — write code"]
        direction LR
        BLD["Builder"]
        DSN["Designer"]
        FRG["Forge"]
        GRD["Guardian"]
        JAN["Janitor"]
        LGL["Legal"]
    end

    T4 --> T5
    subgraph T5["Tier 5 · Support — fast helpers"]
        direction LR
        SCT["Scout"]
        PLN["Planner"]
        QCK["Quick"]
        SKM["Skill-Matcher"]
        MSH["Mesh"]
    end
```

<details>
<summary><b>See the full tier table</b></summary>

<br/>

| Tier | Role | Examples | Writes code? |
|---|---|---|---|
| 1 — Executive | strategy, governance, veto | COO · CTO · CFO · CKO | ❌ govern only |
| 2 — Leadership | coordination & delivery | VP-Eng · HR | ❌ |
| 3 — Management | tracking & lifecycle | Chief-of-Staff · Scrum · Tech-Lead · **Secretary** | ❌ |
| 4 — Specialists | the doers | Builder · Designer · Forge · Guardian · Janitor · **Legal** · Proposal-writer | ✅ full |
| 5 — Support | fast, silent helpers | Scout · Planner · Quick · Skill-Matcher · Mesh | ⚙️ scoped |

*Authority and tool-access are **enforced**, not suggested — separation of powers for AI.*
*(Plus an opt-in **`security`** squad — cyber-operator, ai-sec, recon — for authorized testing.)*

</details>

---

## 🧩 Skills — predicted, not memorized
A large library of capabilities (markdown + logic). High-frequency intents route instantly;
anything novel is matched semantically and surfaced *before you ask*. Drop in a new file and
it's discoverable. LeRoy also **watches your patterns and proposes new skills** *(alpha)*.

## 🔌 MCPs — it builds its own connectors
Speaks [Model Context Protocol](https://modelcontextprotocol.io). LeRoy doesn't ship a pile
of pre-baked third-party connectors — it ships the thing that **makes** them: a built-in
**MCP-builder agent + skill** (see [mcps/](mcps/)). Tell it what you want to talk to and it
scaffolds the server, wires the tools, and drops a local `.env` for your key.
> **`leroy mcp add` → "talk to my Notion" → it builds the connector for you.**
> If it has an API, LeRoy can reach it — nothing to hunt for on a marketplace.

## 🧠 Memory — self-growing, Obsidian-native, never "saved"
A human-readable vault on **your** disk (browse it, `grep` it, own it).
- **Always-on capture** — every conversation is distilled, chunked, embedded. No save button.
- **Confidence decay** — facts you *stated* are permanent; facts it *inferred* decay unless
  re-confirmed, so old guesses don't rot recall.
- **Doc-RAG firewall** — drop in a PDF/DOCX; raw source is retrievable on demand but kept out
  of default recall so summaries surface first.
- **Warm sidecar** — a local RAG service serves recall in milliseconds, ships as Python you
  can read.

```
capture → distill → chunk → embed → graph
```

> **See your brain** — point [Obsidian](https://obsidian.md) at `~/.claude/memory` and open
> **Graph View** to watch your second brain grow: every `[[wiki-link]]` LeRoy writes becomes
> an edge. Plain markdown, no export, no lock-in. *(Obsidian is free.)*

## 🏛️ The Boardroom *(optional — off by default)*
Consequential decisions convene a council — General (act now), Sage (5-yr), Skeptic (what
breaks), Diplomat (people), Architect (structure) — plus an Inquisitor. It votes and logs the
verdict. It's **opt-in** (`leroy add boardroom`) because a 24/7 boardroom uses tokens; a
governor caps spend either way to protect a flat plan.

## 🔧 It runs — and repairs — itself
- **Self-healing auto-fix:** audit → fix → verify → **auto-rollback**, in tiers (safe fixes
  auto, risky ones need approval), with a protected-path wall and git checkpoints.
- **Janitor** audits and cleans the whole system on a schedule.
- **Wake-coalescer** collapses missed jobs into one digest — no task storms.
- **Self-policing automation:** nothing autonomous can create a scheduled job without an
  approved entry in the automation registry.

## ⚡ Deterministic by design — "Position Zero"
Before *every* response a mandatory pre-flight runs: load identity → recall memory → route →
act. Enforced by a hook, not by hoping. This is why LeRoy stays consistent across thousands of
turns instead of drifting — and every gate emission is written to the **gate log** for audit.

---

## 🚧 The desktop app — unlocks at 5,000 stars
A visual companion is built — a 3D globe of your sessions, a kanban triage board, the live
boardroom, an inbox, and drag-and-drop document RAG. It's **not part of this release**: LeRoy
v1 is **CLI-first and fully complete on the command line**, and the desktop app unlocks once
the project hits **5,000 GitHub stars** — a real signal that enough people are relying on the
CLI product to be worth supporting a second surface well, rather than shipping it half-baked
alongside the launch. Star the repo to help get there and get pinged the moment it unlocks.

---

## 🔒 Your data is yours
Memory lives **on your machine** as plain files. API keys stay in local `.env` files that
never enter the repo. LeRoy doesn't phone home. `leroy update` pulls *our* code without
touching *your* grown memory — code and brain are separate layers.

---

<p align="center"><sub>Built by <a href="https://helpmebim.com">HelpMeBIM</a> · MIT · Made with Claude</sub></p>
<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:080a0d,100:2d6cdf&height=100&section=footer" />
</p>
