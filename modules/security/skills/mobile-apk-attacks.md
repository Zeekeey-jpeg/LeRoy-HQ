---
title: Mobile / APK Attacks
created: 2026-03-10
tags: [skills-learned, cyber, mobile]
type: technique
payout_ceiling: $5K–$25K (hardcoded secrets, SSL pinning bypass, exported component abuse)
auth_required: YES (requires device + app install; public account registerable)
autonomy_level: AUTH-CREATABLE
---

# Mobile / APK Attacks

## Concept

Android APKs are ZIP archives containing DEX bytecode, resources, and manifest. Reverse engineering reveals hardcoded secrets, API endpoints, improper TLS validation, exposed components, and insecure storage.

**Primary targets:**
- Hardcoded API keys/secrets in source
- Exported Activities/Services without permission checks
- Insecure data storage (SharedPrefs, SQLite, external storage)
- Improper SSL pinning (bypassable)
- Deeplink/Intent hijacking
- `android:backup="true"` (adb backup extraction)
- `android:debuggable="true"` in production build

---

## Setup & Static Analysis

```bash
# Extract APK from device:
adb pull /data/app/com.target.app-1/base.apk ./target.apk

# Decompile with JADX (primary tool — best Java output):
jadx -d ./output/ target.apk
jadx-gui target.apk  # GUI version

# Decompile with apktool (smali + resources):
apktool d target.apk -o ./output/

# Quick secret grep:
grep -r "api_key\|apikey\|secret\|password\|token\|AWS\|firebase\|Authorization" \
  ./output/sources/ --include="*.java" -i -l

# Deep secret grep with context:
grep -r "api_key\|secret\|password\|token" ./output/sources/ -i -A 2 -B 2

# Check AndroidManifest.xml for dangerous flags:
cat ./output/AndroidManifest.xml | grep -E "exported|permission|debuggable|backup"
# Dangerous flags:
# android:debuggable="true"       → attach debugger
# android:allowBackup="true"      → adb backup extraction
# android:exported="true"         → component accessible to other apps WITHOUT permission

# APKLeaks — hardcoded secret finder:
pip3 install apkleaks --break-system-packages
apkleaks -f target.apk -o leaks.txt

# MobSF — automated static + dynamic analysis:
docker pull opensecurity/mobile-security-framework-mobsf
docker run -it -p 8000:8000 opensecurity/mobile-security-framework-mobsf
# Upload APK at http://localhost:8000
```

---

## Dynamic Analysis — SSL Pinning Bypass

### Method 1 — Patch APK (no root required, works on Android 7+)
```bash
# Android 7+ doesn't trust user certs → patch the APK:
apktool d target.apk

# Add/edit network_security_config.xml:
mkdir -p target/res/xml/
cat > ./target/res/xml/network_security_config.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
  <base-config>
    <trust-anchors>
      <certificates src="system"/>
      <certificates src="user"/>
    </trust-anchors>
  </base-config>
</network-security-config>
EOF

# Reference it in AndroidManifest.xml:
# <application android:networkSecurityConfig="@xml/network_security_config">

apktool b target -o patched.apk

# Sign:
keytool -genkey -v -keystore test.jks -alias test -keyalg RSA -validity 365 -noprompt \
  -dname "CN=Test, OU=Test, O=Test, L=Test, S=Test, C=US" -storepass testpass -keypass testpass
apksigner sign --ks test.jks --ks-pass pass:testpass patched.apk

# Install:
adb install patched.apk
```

### Method 2 — Frida (root/emulator required)
```bash
pip3 install frida-tools --break-system-packages

# Push frida-server to device (match architecture):
adb push frida-server /data/local/tmp/
adb shell "chmod 755 /data/local/tmp/frida-server && /data/local/tmp/frida-server &"

# Run SSL bypass script:
# https://github.com/httptoolkit/frida-android-unpinning
frida -U -f com.target.app -l ssl_bypass.js --no-pause
```

### Method 3 — objection (wraps Frida, easier interface)
```bash
pip3 install objection --break-system-packages
objection -g com.target.app explore

# In objection shell:
android sslpinning disable    # disable certificate pinning
android root disable          # bypass root detection
android clipboard monitor     # capture clipboard
```

---

## Exported Component Testing

```bash
# List attack surface:
# drozer:
drozer console connect
run app.package.attacksurface com.target.app
run app.activity.info -a com.target.app      # exported activities
run app.provider.info -a com.target.app      # content providers

# Direct adb testing:
# Launch exported activity:
adb shell am start -n com.target.app/.AdminActivity
adb shell am start -a com.target.app.HIDDEN_ACTION

# Send intent with extras (deeplink abuse):
adb shell am start -n com.target.app/.DeepLinkActivity \
  -d "target://action?token=attacker-controlled"

# Query content provider:
adb shell content query --uri content://com.target.app.provider/users
```

---

## Insecure Storage (root required)

```bash
adb shell
run-as com.target.app   # on non-rooted debug build

# Check SharedPreferences:
cat /data/data/com.target.app/shared_prefs/com.target.app_preferences.xml

# Check SQLite databases:
ls /data/data/com.target.app/databases/
sqlite3 /data/data/com.target.app/databases/app.db ".tables"
sqlite3 /data/data/com.target.app/databases/app.db "SELECT * FROM users LIMIT 5"

# Check external storage (world-readable):
ls /sdcard/Android/data/com.target.app/
```

---

## Tools & Terminal

```bash
# jadx          → APK decompiler (Java output)    brew install jadx
# apktool       → APK decompiler (smali + res)    apt install apktool
# apkleaks      → secret finder                   pip3 install apkleaks
# MobSF         → full static+dynamic             docker
# objection     → frida wrapper                   pip3 install objection
# frida-tools   → dynamic instrumentation         pip3 install frida-tools
# drozer        → Android attack framework        github
# adb           → Android debug bridge            platform-tools

# Check SSL pinning implementation in source:
grep -r "CertificatePinner\|TrustManager\|checkServer\|X509\|pinnedCertificate\|sha256" \
  ./output/sources/ -r -l
```

---

## Bypass / Edge Cases

- Multiple pinning implementations — may need multiple Frida hooks (OkHttp, WebView, custom)
- Root detection bypass: `android root disable` in objection, or Magisk module
- Emulator detection — check `Build.FINGERPRINT`, `ro.kernel.qemu`
- ProGuard/R8 obfuscation — use JADX renaming heuristics, string decryption
- Flutter apps — extract from `libapp.so` (AOT compiled)
- React Native apps — `index.android.bundle` in assets/
- Hermes bytecode — use `hbc-decompiler`
- Certificate Transparency checks — some apps verify CT logs

---

## Filing Guidance

**Hardcoded API key:** High ($10K–$25K) — show key → verify it's live → show impact (what access it grants)
**Exported component without permission:** High ($10K+) — show unauthorized access via adb command
**SSL pinning bypassable:** Medium ($5K–$10K) — show Burp traffic capture after bypass
**Insecure storage of auth tokens:** High ($10K+) — show token extraction → ATO
**`android:debuggable="true"` in production:** Medium ($5K) — show debugger attachment

Always check: is the app in-scope? (APK name must match program scope list)

---

*Mobile / APK Attacks v1.0 | Ingested 2026-03-10 | Owner: cyber-operator*
