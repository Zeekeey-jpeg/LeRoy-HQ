# Security Policy

## What LeRoy is (and the honest threat model)

LeRoy runs on your machine. It **executes code**, **reads and writes local files**, and can
**hold API keys** for any services you choose to connect. Treat it like any powerful local dev
tool. By design:

- **Your data stays local.** Your memory vault lives on your disk as plain files. LeRoy does not
  phone home.
- **Your keys stay local.** Connector credentials live in local `.env` files that are gitignored
  and never leave your machine.
- **Nothing here contains our secrets.** This public repo is built by an inclusion-only pipeline
  with a fail-closed secret/PII scanner and a gitleaks CI gate — no keys, tokens, or private data
  are published. If you ever find otherwise, please report it (below) — that's a bug we take
  seriously.

## Using it safely

- Review connectors before granting them credentials; use least-privilege API keys.
- Keep your `.env` files out of version control (the shipped `.gitignore` already blocks them).
- LeRoy can take actions on your behalf — read what a skill/agent does before enabling it,
  especially anything that sends email or writes to external systems.

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Email **security@helpmebim.com**
with details and steps to reproduce. We aim to acknowledge within 72 hours.

## No warranty

LeRoy is provided "as is" under the MIT License, without warranty of any kind. You are
responsible for what you connect it to and the actions you let it take.
