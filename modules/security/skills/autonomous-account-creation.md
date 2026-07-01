# Autonomous Account Creation v1.0
**Owner: cyber-operator / Sweep Engine sub-agents**
**Trigger:** Called when Auth-Creatable vector requires account to execute
**Purpose:** Self-service account creation for bounty testing. No check-in required for public registration flows.

---

## Core Rule

```
IF account_type == "public" AND registration_requires == "email_only":
  Auto-create. No check-in. Log the action.

IF registration_requires == "phone_verification":
  Auto-create using temp SMS service. No check-in. Log.

IF registration_requires == "credit_card" OR "KYC" OR "invite_code":
  STOP. Flag as Auth-Gated. Include in auth-gated section of report.
  Do NOT attempt to bypass registration gates.
```

---

## Account Generation Protocol

### Step 1 — Generate Credentials

```
Email: bounty-test-{UUID8}@mailinator.com
       OR: {UUID8}@guerrillamail.com
       OR: {UUID8}@tempmail.plus

Username: BountyTest{UUID4} (if username required)
Password: T3stB0unty!{UUID4} (meets most complexity requirements)
Name: Security Test (first) | Researcher (last)
Phone: Use temp SMS if required (https://receive-smss.com)
```

**UUID generation:** Use first 8 chars of a random hex string.

### Step 2 — Navigate to Registration

```
playwright-cli sequence:
1. playwright-cli open /register, /signup, /create-account, or /join
2. playwright-cli snapshot  # get element refs
3. playwright-cli fill e1 "email" e2 "password" ...  # fill form
4. playwright-cli click e5  # click Create Account / Register / Sign Up
```

### Step 3 — Handle Email Verification

```
If email verification required:
  1. playwright-cli open https://www.mailinator.com/v4/public/inboxes.jsp?to={UUID8}
  2. playwright-cli snapshot  # find verification email
  3. Click verification link OR extract code from email body
  4. playwright-cli goto <verification URL> (if link-based)
  5. If code-based: playwright-cli fill eN "<code>" then submit
  6. Confirm: account active
```

### Step 4 — Handle Phone Verification (if required)

```
1. playwright-cli open https://receive-smss.com (or similar public temp SMS)
2. playwright-cli snapshot  # select available number
3. Use that number in registration form
4. playwright-cli goto <SMS inbox url>
5. playwright-cli snapshot  # find verification SMS → extract code
6. Enter code in registration form
7. Log: "Used temp SMS number [number] for [program name] — expires [when]"
```

### Step 5 — Log Creation

```
Log to session state:
  program: [program name]
  account_email: [email used]
  account_created: [timestamp]
  purpose: "Bounty testing — Auth-Creatable vector execution"
  note_for_report: "Test account created at [email], deleted post-POC"
```

---

## Post-Testing Cleanup

```
AFTER POC is confirmed:
  1. Navigate to account settings → delete account (if option exists)
  2. If no delete option: log account for manual cleanup
  3. Note in report writeup: "Test account [email] created and deleted post-POC"

IF cleanup fails (no delete option):
  Document: account exists, no sensitive data, not exploiting further
  Note in report: "Test account [email] remains but contains only test data"
```

---

## Registration Form Patterns (Common Frameworks)

| Framework / Platform | Registration URL | Notes |
|---------------------|-----------------|-------|
| React/Next.js apps | /register or /signup | Usually JSON API, check /api/auth/register |
| Frappe / ERPNext | /register | May have CAPTCHA |
| Firebase Auth apps | /signup | May use Google/Apple sign-in only |
| Cognito apps | /signup or SDK-based | Pool-specific flow, check hosted UI |
| HackerOne test accounts | N/A | Use the researcher account per protocol |

---

## CAPTCHA Handling

```
IF CAPTCHA detected on registration form:
  1. STOP auto-creation
  2. Flag as Auth-Gated (effectively requires human)
  3. Note: "CAPTCHA blocks autonomous account creation — treat as Auth-Gated"
  4. Include in Auth-Gated section of report with note
  5. Do NOT attempt CAPTCHA solving services (scope/ethics concern)
```

---

## Whitehat Boundaries

```
NEVER:
  - Use real personal information (name, phone, email)
  - Reuse test accounts across programs (one account per program per session)
  - Attempt to bypass KYC, age verification, or invite-only gates
  - Create more than 3 accounts on any single program
  - Store credentials in files

ALWAYS:
  - Use disposable email services
  - Use "Security Test" as name pattern (not deceptive)
  - Log all accounts created in session state
  - Delete accounts post-testing when possible
  - Note account creation in report for full transparency
```

---

*Autonomous Account Creation v1.0 | Whitehating System v2.0*
