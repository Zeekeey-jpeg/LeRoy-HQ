---
name: android-dynamic-analysis
description: "Android APK dynamic analysis skill for CTF and security research. Covers: ADB toolchain, UIAutomator2, Frida setup/hooking/memory scanning, Drozer attack surface enumeration, objection bypass, apktool decompile/repackage, jadx Java decompilation, Playwright Android (WebView only). Use for dynamic APK CTF challenges, Android app reverse engineering, runtime hooking for flag extraction."
trigger_keywords: "android apk, adb, frida, objection, drozer, jadx, apktool, dynamic analysis, android emulator, apk ctf, reverse apk, runtime hook, android instrumentation"
version: 1.0
created: 2026-02-24
owner: cyber-operator
---

# Android Dynamic Analysis Skill

## Purpose

Complete toolkit for dynamic analysis of Android APKs in CTF/security research contexts. Covers the full progression from static decompilation through runtime instrumentation.

---

## Tool Progression (Use in This Order)

```
jadx (read source, find logic) → apktool (patch smali) → objection (quick bypass) → Frida (custom hooks)
```

---

## ADB Core Commands

```bash
adb install -r -t challenge.apk                          # Install
adb shell am start -n com.ctf/.MainActivity              # Launch
adb shell input tap 500 1200                             # Tap
adb shell input text "CTF_input"                         # Type
adb shell input keyevent 66                              # Enter
adb shell "run-as com.ctf cat shared_prefs/prefs.xml"    # Read SharedPrefs
adb shell "run-as com.ctf sqlite3 databases/app.db 'SELECT * FROM flags;'"
adb logcat -d -s "CTF:V" > filtered.txt                 # Filtered logs
```

---

## jadx — Decompile to Java

```bash
jadx -d output/ challenge.apk           # Full decompile
jadx -d decompiled/ --deobf target.apk  # With deobfuscation
jadx-gui challenge.apk                  # Interactive search GUI
```

---

## apktool — Smali Patch & Repackage

```bash
apktool d challenge.apk -o decoded/     # Decompile
# Edit decoded/smali/... to patch checks
apktool b decoded/ -o modified.apk      # Rebuild
apksigner sign --ks ctf.keystore modified.apk  # Sign
```

---

## Frida Setup on Emulator

```bash
pip install frida-tools
VERSION=$(frida --version)
curl -Lo frida-server.xz "https://github.com/frida/frida/releases/download/$VERSION/frida-server-$VERSION-android-x86.xz"
xz -d frida-server.xz
adb root && adb push frida-server /data/local/tmp/
adb shell "chmod 755 /data/local/tmp/frida-server && /data/local/tmp/frida-server &"
```

## Frida — Method Hook Template

```javascript
Java.perform(() => {
    const Target = Java.use('com.ctf.ClassName');
    Target.methodName.implementation = function(arg1) {
        console.log('[*] Called with: ' + arg1);
        const result = this.methodName(arg1);
        console.log('[*] Returns: ' + result);
        return true;  // Override return value
    };
    // Call static method directly
    console.log(Java.use('com.ctf.Helper').getFlag(0));
});
```

## Frida — Memory Scan for "CTF{"

```javascript
var mod = Process.findModuleByName("libnative.so");
Memory.scan(mod.base, mod.size, "43 54 46 7B", {  // "CTF{"
    onMatch: function(addr) { console.log(hexdump(addr, {length: 64})); }
});
```

## Frida — Python Host Script

```python
import frida, sys
device = frida.get_usb_device()
pid = device.spawn(["com.ctf.app"])
session = device.attach(pid)
script = session.create_script(open("hook.js").read())
script.on('message', lambda m, d: print(m['payload']))
script.load()
device.resume(pid)
sys.stdin.read()
```

---

## objection — Quick Runtime Bypass

```bash
objection -g com.ctf.app explore
> android sslpinning disable
> android hooking list classes
> android hooking watch class com.ctf.MainActivity --dump-args --dump-return
```

Non-rooted: `objection patchapk --source app.apk`

---

## Drozer — Attack Surface Enumeration

```bash
adb install drozer-agent.apk && adb forward tcp:31415 tcp:31415
drozer console connect
> run app.package.attacksurface com.ctf.app
> run app.activity.info -a com.ctf.app
> run app.provider.info -a com.ctf.app
> run scanner.provider.finduris -a com.ctf.app
> run app.provider.query content://com.ctf.app.provider/flags
> run scanner.provider.sqltables -a content://...
```

---

## UIAutomator2 — Selector-Based UI Control (Better Than ADB Coords)

```python
import uiautomator2 as u2
d = u2.connect('emulator-5554')
d.app_start("com.ctf.app")
d(text="Login").click()
d(resourceId="com.ctf:id/input").set_text("flag_attempt")
```

---

## Playwright Android — WebView Only (Node.js)

```javascript
const { _android: android } = require('playwright');
const [device] = await android.devices();
const webview = await device.webView({ pkg: 'com.ctf.app' });
const page = await webview.page();
// Then use standard Playwright page API
```

**Limitations:** No native UI, no Python, no swipe/pinch.
**Pattern:** ADB navigates to WebView screen → Playwright handles DOM.

---

## Headless Emulator Setup for CI

```bash
sdkmanager "system-images;android-30;google_apis;x86_64"
echo "no" | avdmanager create avd --force --name ctf \
  --package "system-images;android-30;google_apis;x86_64" --device pixel
emulator @ctf -no-window -no-audio -no-boot-anim -gpu swiftshader_indirect -writable-system &
adb wait-for-device
adb shell 'while [[ "$(getprop sys.boot_completed)" != "1" ]]; do sleep 1; done'
```

**Docker:** `budtmo/docker-android` — requires `/dev/kvm`. ~4GB RAM, 2 CPU, 10GB disk.

---

## Vault References

- `memory/Skills-Learned/Android-CTF-Dynamic-Analysis.md` — full code reference
- `memory/Skills-Learned/JWT-Attack-Playbook-Android-CTF.md` — JWT attacks from intercepted APK traffic
- `a technique-reference note` — orchestration architecture
- `skills/domains/cyber/mitmproxy-agent-workflow.md` — traffic interception setup

---

*Android Dynamic Analysis v1.0 | cyber-operator | 2026-02-24*
