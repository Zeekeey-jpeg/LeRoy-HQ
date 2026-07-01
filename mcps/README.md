# Connectors (MCP)

LeRoy speaks the [Model Context Protocol](https://modelcontextprotocol.io) — the open standard
for giving an AI tools to talk to external systems. But LeRoy **doesn't ship a marketplace of
pre-baked third-party connectors.** It ships the thing that *makes* them.

> **Plain-English version:** instead of handing you a drawer full of adapters and hoping one
> fits your outlet, LeRoy comes with a machine that stamps out the exact adapter you need,
> on demand.

---

## The MCP-builder

The headline is the **MCP-builder agent + skill.** Tell LeRoy what you want to connect to and
it scaffolds the server for you:

```
leroy mcp add        # then describe the system: "talk to my Notion"
```

It clones the template below, helps you define the tools, and drops a local `.env` for your
key. If a system has an API, LeRoy can reach it — nothing to hunt for on a registry.

---

## `_template/`

Every new connector starts from [`_template/`](_template/). It's a minimal, working MCP server
(TypeScript, using the official `@modelcontextprotocol/sdk`) with:

- a health-check `ping` tool you replace with your own,
- an example of a tool that takes input and reads a secret from the environment,
- the two rules that matter most:
  1. **Read secrets from the environment** (see `.env.example`) — never hardcode keys.
  2. **Keep each tool small and well-described** — the description is what LeRoy reads to
     decide when to call it.

`leroy mcp add` copies this folder, renames it, and walks you through filling in real tools.

---

## Optional memory backends

Connectors aren't only for outside apps — you can also plug in an **external memory store** as
a recall backend. LeRoy's default memory is a plain-file vault + local RAG sidecar (no database,
nothing to set up), but memory is pluggable. Point it at an external store via `leroy mcp add`:

| Backend | Notes |
|---------|-------|
| **cognee** | Ships its own MCP server — connect it directly. |
| **Neo4j** | Graph store for richer entity/relationship recall. |
| **pgvector** | Postgres + vector search if you already run Postgres. |

The vault stays the source of truth on your disk; the external store becomes an additional
recall layer. Optional, one command, swappable any time.

---

## Keys & safety

Keys live in local `.env` files that never enter version control (the repo `.gitignore` blocks
them). Each connector reads its own key from the environment. LeRoy doesn't phone home, and no
connector ships with credentials baked in.
