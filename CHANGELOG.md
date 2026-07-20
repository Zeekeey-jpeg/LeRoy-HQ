# LeRoy UI — Changelog

## v0.1.1 — 2026-07-20

### Fixes — installer first-run experience

**Reported via:** internal test on a fresh Windows machine (bscott@twgsecurity.com, 2026-07-20):
the installer appeared to do nothing (spinner, then silence), no icon in Start, no
Desktop shortcuts, and the Start Menu entry dropped straight into a raw PowerShell
console with manual CLI instructions.

**Root cause:** the installer and the CLI setup flow never actually talked to each
other. The "Install it for me" button on the setup wizard's brain step opened a
brand-new visible console running the full CLI installer — the exact console users
were landing in. Separately, a missing error handler meant a bundled-backend spawn
failure (e.g. blocked by antivirus on a fresh machine) crashed the whole app with no
window at all, which is what "spinner, then silence" actually was.

**Fixed:**

- **No more silent crash.** The Electron shell now catches a backend spawn failure
  and shows an error screen instead of vanishing.
- **No more console window, ever.** The brain-install step now runs in the
  background with a real in-app progress screen — it used to shell out to a raw
  PowerShell console running the CLI installer.
- **Real onboarding interview in the app.** A question-by-question setup screen
  replaces the old hand-off to a terminal `leroy init`; every answer saves
  immediately, so closing early never loses progress. Ends on a "LeRoy is ready to
  use" screen that launches the app.
- **Both Desktop shortcuts, reliably.** "Leroy CLI" and "LeRoy UI" are both created
  using the same OneDrive/Known-Folder-Move-safe resolution that previously only
  covered the CLI shortcut — this is why some machines showed zero or blank icons.
- **`leroy start` now actually launches the app** instead of printing a stub message.
- Installer launches automatically when setup finishes (`runAfterFinish: true`).
- Setup wizard footer no longer points a desktop-app user at the CLI.

---

## v0.1.0 — 2026-07-17

Initial public release of LeRoy UI (Windows desktop app).

- Bundled FastAPI backend + React frontend in a single NSIS installer
- SetupGate wizard walks fresh installs through Claude Code CLI, git, Node, Python,
  and the LeRoy brain
- Session tabs, Kanban triage, Board Room panel, Activity + Memory views
- Auto-update via GitHub Releases (electron-updater)
