# LeRoy UI — Changelog

## v0.1.1 — 2026-07-20

### Bug fixes — installer first-run experience

**Reported via:** internal test on a fresh Windows machine (bscott@twgsecurity.com, 2026-07-20)

**Issues fixed:**

- **Installer no longer exits silently.** Added `runAfterFinish: true` to the NSIS
  config so LeRoy UI launches automatically when the installer finishes — users no
  longer have to hunt for the app in Start or Windows Search.

- **Setup wizard: brain step now explains the console window.** When a user clicks
  "Install it for me" on the LeRoy brain step, a console opens and runs the
  install script. A note now tells them to wait for it to finish and then click
  "I did it — check again" to return to the wizard — previously this was silent
  and confusing.

- **Setup wizard: footer no longer pushes users toward the CLI.** The old footer
  read "Prefer the terminal? Get LeRoy CLI" — the wrong message for someone who
  just installed the desktop app. It now reads "Need help? View the setup guide"
  and links to the README install section.

---

## v0.1.0 — 2026-07-17

Initial public release of LeRoy UI (Windows desktop app).

- Bundled FastAPI backend + React frontend in a single NSIS installer
- SetupGate wizard walks fresh installs through Claude Code CLI, git, Node, Python,
  and the LeRoy brain
- Session tabs, Kanban triage, Board Room panel, Activity + Memory views
- Auto-update via GitHub Releases (electron-updater)
