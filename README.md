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
  <img src="https://img.shields.io/badge/status-alpha-e09b2d?style=for-the-badge" />
  <img src="https://img.shields.io/badge/built%20on-Claude%20Code-2d6cdf?style=for-the-badge" />
  <img src="https://img.shields.io/badge/memory-Obsidian%20native-8a5cf6?style=for-the-badge" />
  <img src="https://img.shields.io/badge/license-MIT-16243f?style=for-the-badge" />
  <img src="https://img.shields.io/github/stars/Zeekeey-jpeg/LeRoy-HQ?style=for-the-badge&color=2d6cdf" />
</p>

<p align="center">
  <a href="#-choose-your-path">Quickstart</a> ·
  <a href="#-the-org-chart--27-agents-5-tiers">Architecture</a> ·
  <a href="docs/">Docs</a> ·
  <a href="#-see-it-work">Demo</a> ·
  <a href="#-follow-along">Community</a>
</p>

---

## What is LeRoy?

**LeRoy turns your Claude Code into a self-growing AI *company* that runs under you — from the command line.**

Not a chatbot. Not a folder of agent prompts. A whole org — a chief-of-staff, a C-suite,
and a bench of specialists — on a **shared, permanent memory** that learns how *you* work
and gets sharper every day.

You talk to it like a team. It routes each request to the right "employee," remembers every
decision, debates the big calls in a boardroom, grows its own skills as it watches you — and
it does the plumbing (memory, routing, cost control) invisibly.

> **One-liner:** *You know how, if you hired a team, after a few months they'd just know how
> you like things done? LeRoy is that — as software. An AI company that learns you.*

```console
$ leroy
◆ LeRoy online — 27 agents, memory warm.
you › draft the follow-up to yesterday's proposal
◆ [COO] routing → builder + voice-compose · recalling 4 related notes…
◆ done. draft written in your voice, parked in Drafts. logged to memory.
```

### 🕐 Recent
- **2026-07-01** — Doc-RAG ingestion pipeline shipped: drop in a PDF/DOCX, chat over it now, remembered forever.
- **2026-07-01** — Scaling protocol documented ([docs/scaling.md](docs/scaling.md)) — tiers, topology, A2A mesh, CTO flight plans.
- **2026-07-01** — MCP-builder + `_template/` published — LeRoy builds its own connectors on demand.

### By the numbers
**1,063** gate checks at **100%** compliance in daily use · warm recall **3251ms → 1622ms** ·
A2A mesh **2–10×** speedup on parallel work · **27** agents across **5** governed tiers ·
your memory is **100% yours** — plain markdown on your disk.

**Tested + audited:** a dedicated `simulator` agent runs the protocol-compliance harness —
**1,063 gate checks logged at 100% compliance** is our eval story, not a slogan. And every
run leaves a trail: a **gate log**, an **automation registry**, and a **decisions ledger** you
can `grep` after the fact.

---

## 🏆 Why this isn't "another pile of agents"

Anyone can drop 30 agent prompts in a folder — that's the slop. LeRoy is a **system with a
control plane.** The value is the connective tissue *between* the agents:

| Everyone has… | **LeRoy has instead…** |
|---|---|
| A bag of agents you wire yourself | A **governed org chart** — one router, 5 tiers, enforced tool-access |
| Tools you call by name | Skills that are **predicted for you**, not memorized |
| A vector store you dump text into | A memory that **forgets the right things** (confidence decay) |
| "Save to memory" buttons | **Zero-effort capture** — every conversation auto-distilled & embedded |
| One model, one opinion | A **boardroom** that debates consequential calls before you commit |
| Vibes-based behavior | A **deterministic pre-flight** before every turn (recall → route → act) |
| Bit-rot as it grows | It **heals and cleans itself** — audit → fix → verify → rollback |

**The tell for a technical reader:** LeRoy is *deterministic* (a mandatory gate guarantees
recall + routing every turn — 1,063 logged at 100% compliance), *governed* (agents have a
tool-access matrix — the C-suite literally can't write to disk), and *self-repairing* (a
tiered auto-fix engine edits code in isolated git worktrees and rolls back on failure). Every
safety rail traces to a real past incident, with the post-mortem in the docstring. That's an
operating system, not a prompt dump.

---

## 🔬 A reasoning layer on top of the model

LeRoy doesn't just *run on* a reasoning model — it adds a second layer of **algorithmic
instinct** on top, without slowing the machine down. Before it closes a fix, it reflexively
asks: *is this isolated or systemic? what else shares this code or data? does the fix cover
every instance of the problem, not just the one you named?* A defect report can't shortcut to
a knee-jerk single-file change — it's classified first (**root cause → blast radius → cheapest
confirming check**). Fast, but never tunnel-visioned: it fixes the *class* of problem, not just
the instance in front of it.

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

## 🎬 See it work

<p align="center"><i>route a request → boardroom debate → it remembers forever</i></p>

Real jobs LeRoy runs, start to finish:

- **"Draft the follow-up to yesterday's proposal."** → routes to the builder, recalls the thread
  from memory, writes it *in your voice*, and parks it in your drafts.
- **Overnight, unprompted:** a build breaks → LeRoy audits itself, fixes it in an isolated branch,
  verifies, and rolls back if it made things worse — you wake up to a green system and a note
  explaining what it did.
- **"Should we take this on?"** → the boardroom convenes, five personas debate it, you get a
  verdict — and the reasoning is logged to memory forever.

---

## 🚦 Choose your path

LeRoy meets you where you are. Pick the on-ramp that fits:

### 🌱 New here (new to Claude Code, not very technical)
You'll be talking to your AI company in ~15 minutes — no jargon.
```bash
# 1. install Claude Code (one installer — link in docs)
# 2. get LeRoy:
git clone https://github.com/Zeekeey-jpeg/LeRoy-HQ leroy && cd leroy && ./setup
leroy init      # a friendly interview builds your brain
leroy           # start talking (the terminal is the full experience)
```
`leroy doctor` explains any problem in plain English. `leroy reset` undoes everything. No commands to memorize — LeRoy predicts what you need.
LeRoy can also create a desktop shortcut so you just double-click to launch it.

### 🔁 Already use Claude Code
Adopt LeRoy **without losing your setup.**
```bash
./setup                 # detects your ~/.claude, backs it up, merges LeRoy in additively
# memory, mesh & gate are core (installed above). Add the opt-in modules when ready:
leroy add boardroom     # or: leroy add security  (auth-gated)
```
Your existing skills and settings are preserved. `leroy update` later pulls improvements and **never touches your memory.**

<details>
<summary><b>🧠 Expert / builder — bend it to your will</b></summary>

<br/>

- Read `docs/architecture.md` + `docs/hidden-features.md` — the gate, hooks, A2A mesh, self-heal.
- Read `docs/scaling.md` — the tier system, topology selection, mesh hop limits, and the CTO flight plan.
- Scaffold your own: the `agent-creator` / `skill-creator` skills generate new agents & skills; `leroy mcp add` builds connectors on demand.
- Cherry-pick modules; enable the auth-gated `security` module (`leroy add security`).
- Contribute agents / skills / connectors back — see `CONTRIBUTING.md`.

</details>

> **Requires:** a Claude subscription. Node 18+, Python 3.11+, git.
> **Windows-first today**; macOS/Linux in progress.

### 💳 Which Claude plan?
LeRoy runs on a **Claude subscription** — interactive, hands-on use is comfortable on
**Pro**. For the autonomous features (**especially the boardroom**, which can run around the
clock), we recommend **Claude Max (~$100/mo)** so background work doesn't crowd out your own.

**No local model required.** Everything runs on your Claude plan out of the box. A local model
(e.g. [Ollama](https://ollama.com)) is **optional** — add one and LeRoy will offload cheap
background work to it for free; skip it and nothing breaks, it just all runs on Claude.

---

## 🧭 The org chart — 27 agents, 5 tiers

Every request enters one front door (the **COO**). It sizes the job and answers, delegates,
or deploys a team. Agents also talk **peer-to-peer** (A2A mesh — DELEGATE / SUBSCRIBE / CACHE,
with hop limits + circuit breakers) for 2–10× speedup on big jobs. LeRoy scales the crew to
the *shape* of the work — see [docs/scaling.md](docs/scaling.md).

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
- **Warm sidecar** — a local RAG service (numpy fast-path, rerank, knowledge-graph) serves
  recall in milliseconds. Ships as Python you can read.

**The ingestion pipeline:** every document and conversation flows through one line —

```
capture → distill → chunk → embed → graph
```

capture the raw text → distill it to what matters → chunk for retrieval → embed each chunk →
link it into the knowledge graph. That's how a dropped PDF becomes something LeRoy can reason
over minutes later.

> **📊 See your brain — it's an [Obsidian](https://obsidian.md) vault.** Point Obsidian at
> `~/.claude/memory` and open **Graph View** to watch your second brain grow: every `[[wiki-link]]`
> LeRoy writes becomes an edge, every auto-tag a cluster. Your memories, visualized — no export, no
> lock-in. It's plain markdown, so any Markdown tool works too. *(Obsidian is free.)*

### Memory backends — pluggable
LeRoy works **out of the box** with its plain-file Obsidian vault + local RAG sidecar — no
database, no cloud, nothing to set up. But memory is a **pluggable backend.** If you'd rather
back your recall with an external store, plug one in via `leroy mcp add` — e.g. **[cognee](https://github.com/topoteretes/cognee)**
(which ships its own MCP server), **Neo4j**, or **pgvector**. The vault stays the source of
truth on your disk; the external store becomes an additional recall layer. Optional, one command,
swap it any time.

## 🏛️ The Boardroom
Consequential decisions convene a council — General (act now), Sage (5-yr), Skeptic (what
breaks), Diplomat (people), Architect (structure) — plus an Inquisitor. It votes and logs the
verdict. If you run a local model, LeRoy routes ~65% of the low-stakes turns to it for free
and pins only the high-stakes calls to the top model; **without one, everything runs on your
Claude plan** — a 24/7 boardroom will use tokens, which is exactly why it's **opt-in** (see
["Autonomy is opt-in"](#-autonomy-is-opt-in-the-working-car)). A governor caps spend either
way to protect a flat plan.

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

## 🖥️ The desktop app (coming in v1.1)
A visual companion is in the works — a 3D globe of your sessions, a kanban triage board, the
live boardroom, an inbox, and drag-and-drop document RAG. It's **not in this release**: LeRoy
v1 is **CLI-first and fully complete on the command line.** `leroy start` will launch the app
once it lands.

---

## 🔒 Your data is yours
Memory lives **on your machine** as plain files. API keys stay in local `.env` files that
never enter the repo. LeRoy doesn't phone home. `leroy update` pulls *our* code without
touching *your* grown memory — code and brain are separate layers.

---

## 📊 Status — honest edition

<details>
<summary><b>See the full subsystem status table</b></summary>

<br/>

| Subsystem | State |
|---|---|
| COO routing + 5-tier mesh + A2A + soft-interrupts | ✅ |
| Deterministic gate (Position Zero) | ✅ |
| Self-growing memory (vault + RAG + decay + doc firewall) | ✅ |
| Skill library + predictive router | ✅ |
| Boardroom + governor + local-model routing | ✅ |
| MCP builder (build connectors by asking) | ✅ |
| Self-healing auto-fix / janitor / wake-coalescer | ✅ |
| Voice: input (Whisper) + write-in-your-voice compose | ✅ (text-out only) |
| `security` module (authorized-testing arsenal) | ✅ opt-in, auth-gated |
| Desktop visual app (globe, kanban, boardroom) | 🟡 In development — CLI-first for v1 |
| Self-learning loop (auto-*adopt* new skills) | 🟡 Alpha — observes today |
| Typed memory edges (supersedes/contradicts) | 🟡 Roadmap (entity graph in RAG today) |
| One-command installer + cross-platform (mac/Linux) | 🟡 In progress (Windows-first) |

</details>

---

## 🗺️ Roadmap
- [ ] Cross-platform one-command installer + `leroy init` wizard
- [ ] Close the self-learning loop (observe → propose → validate → adopt)
- [ ] Skill & MCP sharing hub
- [ ] Boardroom auto-invoke on consequential decisions
- [ ] Desktop visual app (globe · kanban · boardroom · doc-RAG) — v1.1

---

## ⭐ Follow along
Star the repo — LeRoy ships constantly. Want release pings? [Join the list](#).

<p align="center"><sub>MIT · Made with Claude</sub></p>
<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:080a0d,100:2d6cdf&height=100&section=footer" />
</p>
