---
name: browser-extension-security
description: "Browser extension security testing methodology for authorized security testing. Covers: manifest.json analysis (over-permissioned host_permissions, externally_connectable, web_accessible_resources, unsafe-eval CSP, nativeMessaging), XSS in extension contexts (background page, content script), message passing exploitation (externally_connectable → SSRF/ATO), content script isolation testing. Medium-High bounty ceiling (extension RCE, session theft from all tabs). Unique vertical most hunters skip — FULL autonomy in whitehat-protocol."
trigger_keywords: "browser extension, chrome extension, extension security, manifest.json, content script, background script, extension xss, externally connectable, web accessible resources, chrome.runtime, extension message, crx, extension permissions, extension vuln, extension rce, extension ato"
version: 1.0
created: 2026-02-25
owner: cyber-operator
---

# Browser Extension Security Testing

## Purpose

Test browser extensions with elevated privileges. XSS in extension context grants attacker all extension permissions (access to all tabs, cookies, network requests). Unique vertical most hunters skip. FULL autonomy in whitehat-protocol.

---

## Extension Architecture

```
├── Background Script (Service Worker in MV3)
│   ├── Full extension API access
│   ├── Cross-origin requests without CORS
│   └── Most privileged context
├── Content Scripts
│   ├── Injected into web pages matching URL patterns
│   ├── Access/modify page DOM
│   ├── Isolated JS execution (shared DOM)
│   └── Bridge between page and extension
└── Popup / Options Pages
    ├── Extension-hosted HTML
    ├── Full extension API access
    └── User-initiated
```

---

## Step 1 — Obtain Extension Source

```bash
# From filesystem (Chrome)
~/.config/google-chrome/Default/Extensions/[EXTENSION_ID]/[VERSION]/

# Download CRX from Chrome Web Store
# Use: CRX Extractor browser tool or crxextractor.com
# .crx is a ZIP archive — unzip directly
unzip extension.crx -d extension_source/
```

---

## Step 2 — Manifest Analysis

```json
// High-risk manifest indicators:
{
  "permissions": [
    "<all_urls>",          // Can access ANY website
    "tabs",                // Can read all tab URLs
    "cookies",             // Can read/write any domain cookies
    "webRequest",          // Can intercept all network requests
    "webRequestBlocking",  // Can modify all network requests
    "nativeMessaging",     // Can communicate with native apps
    "debugger",            // Can attach Chrome DevTools to any tab
    "clipboardRead"        // Can read clipboard
  ],
  "content_scripts": [{"matches": ["<all_urls>"]}],  // Injected everywhere
  "content_security_policy": "script-src 'self' 'unsafe-eval';",  // Allows eval()
  "externally_connectable": {
    "matches": ["*://*.target.com/*"]  // Web pages can message the extension
  },
  "web_accessible_resources": ["*"]   // All resources fingerprintable from web
}
```

**Risk matrix:**

| Feature | Risk |
|---|---|
| `<all_urls>` | Extension touches every website |
| `unsafe-eval` in CSP | XSS → arbitrary code in extension context |
| `externally_connectable` with broad matches | Web pages can trigger extension actions |
| `nativeMessaging` | Potential RCE on local system |
| Content scripts on `<all_urls>` | Extension code runs on every page |

---

## Step 3 — JavaScript Source Review

Search for vulnerable patterns:

```javascript
// Dangerous sinks
innerHTML, document.write, eval(), Function()

// Message passing (trace data flow)
chrome.runtime.sendMessage()        // Content script → background
chrome.runtime.onMessage.addListener()  // Message receiver
chrome.runtime.sendMessage(EXT_ID, ...) // External page → extension

// Cross-origin requests in background
fetch(), XMLHttpRequest             // Background can bypass CORS

// User-controlled data flowing into privileged operations
chrome.tabs.create({url: USER_INPUT})
chrome.scripting.executeScript({...code: USER_INPUT})
```

**Vulnerable pattern example:**
```javascript
// content.js reads page data, sends to background
var data = document.querySelector('#data').textContent;
chrome.runtime.sendMessage({type: "pageData", data: data});

// background.js renders it (VULNERABLE)
chrome.runtime.onMessage.addListener(function(msg) {
  document.getElementById('display').innerHTML = msg.data;  // XSS in extension context
});
```

---

## Step 4 — Test External Message Passing

```javascript
// From DevTools console of any web page:
chrome.runtime.sendMessage("EXTENSION_ID_HERE", {test: "probe"}, function(resp) {
  console.log("Response:", resp);
  console.log("Error:", chrome.runtime.lastError);
});
// No lastError → extension accepts external messages from your origin

// If extension accepts: analyze background.js message handler for:
// SSRF via fetch, ATO via stored credentials, tab manipulation, cookie theft
```

---

## Step 5 — SSRF via Extension

```javascript
// If externally_connectable allows your page to message the extension:
chrome.runtime.sendMessage("EXTENSION_ID", {
  action: "fetch_url",
  url: "http://169.254.169.254/latest/meta-data/"  // Extension fetches this (no CORS)
}, function(response) {
  console.log(response);  // Extension returns AWS metadata
});
```

---

## Evidence Standards

- XSS in extension: Show payload executing in extension context, demonstrate access to `chrome.*` APIs (e.g., `chrome.tabs.query` call successful).
- Message passing exploit: Show external message → privileged extension action (SSRF response, cookie theft, tab manipulation).
- Manifest risk: Document each high-risk permission and its exploitation potential.

*browser-extension-security.md v1.0 | owner: cyber-operator | 2026-02-25*
