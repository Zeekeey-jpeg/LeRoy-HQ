# Contributing to LeRoy-HQ

Thanks for wanting to make LeRoy better. LeRoy is a local-first AI operator you can
extend with **skills** (things it knows how to do), **agents** (specialists it can spawn),
and **connectors** (MCP servers that let it talk to your tools). Most contributions are just
a markdown file or a small connector — no deep internals required.

## Quick start

1. **Fork** the repo and clone your fork.
2. Create a branch: `git checkout -b feat/my-thing`.
3. Make your change (see the recipes below).
4. Run the checks (see [Running the checks](#running-the-checks)).
5. Open a pull request against `master`.

## Ways to contribute

### Add a skill

A skill is a single markdown file describing a task LeRoy can do. Drop it into `skills/`
(pick the closest subfolder, e.g. `skills/workflows/`, `skills/tooling/`).

- Give it a clear, action-oriented name: `skills/tooling/summarize-pdf.md`.
- Start with a one-line description of when the skill should fire.
- Then list the steps LeRoy should follow. Write it like instructions to a capable teammate.
- Keep it self-contained — link to other skills instead of duplicating them.

That's it. No code required for most skills.

### Add an agent

An agent is a specialist LeRoy can delegate to. Add a markdown file under `agents/` with:

- **Name and one-line purpose** at the top.
- **When to use it** — the triggering conditions.
- **What it owns** and, if relevant, which tools it should be limited to.

Keep agents narrow. A focused agent that does one thing well beats a broad one.

### Build a connector (MCP server)

Connectors let LeRoy talk to any system with an API. The fastest path:

```bash
leroy mcp add        # conversational connector builder
```

Or start from the template by hand:

1. Copy `mcps/_template/` to `mcps/<your-connector>/`.
2. Edit `src/index.ts` — register one small, well-described tool at a time.
3. Read every secret from the environment. See the template's `.env.example`.
   **Never hardcode keys, tokens, or URLs with credentials in them.**
4. The tool `description` is what LeRoy reads to decide when to call it — make it precise.

## Coding conventions

- **Small and readable.** Match the style of the file you're editing.
- **No secrets, ever.** API keys, tokens, and personal data live in local `.env` files
  (gitignored). Nothing private belongs in a commit. See below.
- **No private/personal data.** Don't include real names, client data, internal hostnames,
  or absolute paths from your own machine. Keep examples generic.
- **Descriptions over cleverness.** For skills and tools, a clear description beats terse code.
- **Python** should pass `python -m py_compile`. **Markdown** should be valid and render cleanly.

## Running the checks

Before opening a PR, run what CI runs:

```bash
# Compile every Python file (catches syntax errors)
find . -name '*.py' -not -path '*/node_modules/*' -print0 | xargs -0 -n1 python -m py_compile

# Secret scan (install gitleaks: https://github.com/gitleaks/gitleaks)
gitleaks detect --no-banner --redact
```

CI runs both automatically on every pull request.

## Secret scanning

**Every pull request is automatically scanned for secrets with
[gitleaks](https://github.com/gitleaks/gitleaks).** A finding fails the build. If you think a
match is a false positive, mention it in the PR — do not disable the scan. If you ever discover
a real secret has been committed, treat it as compromised: rotate it immediately and report it
per [SECURITY.md](SECURITY.md).

## Pull request process

1. Keep PRs focused — one feature or fix per PR.
2. Fill out the PR template, including the checkbox confirming no secrets or PII are included.
3. Make sure CI is green (secret scan + lint).
4. A maintainer will review. We aim to respond promptly.

## Code of conduct

By participating you agree to our [Code of Conduct](CODE_OF_CONDUCT.md).

Happy building.
