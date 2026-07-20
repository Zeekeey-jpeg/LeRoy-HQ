# LeRoy UI — setup guide

## Requirements

LeRoy UI needs these on your machine — the app checks each one on first launch
and offers to install anything missing:

- Windows 10/11 (64-bit)
- [Claude Code CLI](https://claude.com/claude-code), signed in
- [git](https://git-scm.com/downloads)
- [Node.js 18+](https://nodejs.org/)
- [Python 3.11+](https://www.python.org/downloads/) — check **"Add python.exe to PATH"** during install

## Install

1. [Download the installer](https://github.com/Zeekeey-jpeg/LeRoy-HQ/releases/latest/download/LeRoy-UI-Setup.exe).
2. Run it — it asks for confirmation, then installs everything with no console
   window at any point.
3. Answer the onboarding questions. Each answer saves immediately, so closing
   early never loses progress — just relaunch the app to pick up where you
   left off.
4. You'll end up with two Desktop shortcuts: **Leroy CLI** and **LeRoy UI**.

## Common issues

**"Something went wrong: no system Python found"**
Python 3.11+ isn't on this machine's PATH. Install it from
[python.org](https://www.python.org/downloads/), checking "Add python.exe to
PATH", then retry the step — no need to reinstall LeRoy UI itself.

**Antivirus flags the installer, or Windows SmartScreen blocks it**
LeRoy UI isn't code-signed yet (small open-source project, no cert). Click
"More info → Run anyway" on the SmartScreen prompt, or add an exception in
your antivirus. This is expected for an unsigned `.exe` downloaded from the
internet — always verify you got it from
[this repo's Releases page](https://github.com/Zeekeey-jpeg/LeRoy-HQ/releases)
and nowhere else.

**Desktop shortcuts didn't appear**
Re-run the installer once — the first run creates your `~/.claude` folder;
if anything interrupts that first run (a SmartScreen prompt, antivirus scan),
shortcut creation can land on the second run instead. If they still don't
show up, check whether OneDrive has redirected your Desktop folder
(File Explorer → Desktop in the sidebar — does it show a cloud icon?);
shortcuts are still created correctly either way, but it's worth knowing
which Desktop you're looking at.

**Landed in a raw PowerShell console instead of the app**
That shouldn't happen as of v0.1.1 — please
[open an issue](https://github.com/Zeekeey-jpeg/LeRoy-HQ/issues/new) with
what you clicked right before it happened.

## Still stuck?

[Open an issue](https://github.com/Zeekeey-jpeg/LeRoy-HQ/issues/new) with:
- What you clicked / typed right before the problem
- The exact error text, if any
- Windows version, and whether OneDrive manages your Desktop/Documents
