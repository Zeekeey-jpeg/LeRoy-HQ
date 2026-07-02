# LeRoy Web UI — Auth Setup

LeRoy's web UI is **local-only and unauthenticated by design**. There is no login,
no account, and nothing to configure — it just opens.

## What this means

- The web UI binds to `127.0.0.1` (your own machine only) and starts with **no
  sign-in step**. If you can see it in a browser, it's because you're on the
  same machine it's running on.
- This matches how you'd use LeRoy day to day: mainly through the CLI, with the
  web UI as an optional local conversation window — not a hosted app, not a
  multi-user service.
- Because there's no login screen, anyone who can open a browser tab on your
  machine can use LeRoy through the web UI, the same as anyone who can open a
  terminal on your machine can use the CLI. Treat access to your machine as the
  security boundary — the same way you already do for every other local dev
  tool you run.

## ⚠️ Do not expose this to the internet without adding your own auth first

> **If you run `tailscale funnel`, `tailscale serve`, ngrok, port-forwarding,
> or any other tool that exposes a local port to the internet or your LAN,
> you are exposing an UNAUTHENTICATED application with the ability to take
> actions on your machine — read/write files, run commands, and use whatever
> accounts or API keys you've connected it to.**
>
> Do not do this unless you understand the risk and have put your own
> authentication in front of it (a reverse proxy with basic auth, a VPN-only
> tunnel, an OAuth gate, etc.). LeRoy's web UI does not include a login layer
> — it was intentionally left out to keep the local, single-user experience
> as simple as possible. Adding one back in for remote access is on you.

## Why it's built this way

LeRoy is designed to run on your own machine, for you, the same trust model as
any local CLI tool or dev server. Building in a login system would have added
complexity (accounts, sessions, password/OAuth flows) for a scenario — a
single local user on their own machine — that doesn't need one. If you want to
reach LeRoy from another device, the supported path is opening it locally on
that device (or a private, authenticated tunnel you set up yourself), not
exposing the raw local server to the public internet.

## Reporting a concern

If you find a way for a *local* request to do something it shouldn't (privilege
escalation, sandbox escape, etc.), that's a real vulnerability — see
`SECURITY.md` for how to report it. Exposing the unauthenticated local server
to the internet yourself is a configuration choice, not a vulnerability in
LeRoy, but we're happy to hear suggestions for making that mistake harder to
make by accident.
