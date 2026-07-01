# Version Management Protocol

## Version Increment Rules

**MANDATORY:** Every substantial code change MUST increment the version number.

### Semantic Versioning: MAJOR.MINOR.PATCH.BUILD

- **MAJOR** (1.x.x.x) - Breaking changes, major rewrites
- **MINOR** (x.1.x.x) - New features, significant enhancements
- **PATCH** (x.x.1.x) - Bug fixes, refactors, small improvements
- **BUILD** (x.x.x.1) - Build number (usually auto-incremented or date-based)

### When to Increment

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| New command/feature | MINOR | 1.0.x → 1.1.0 |
| Major refactor | PATCH | 1.0.4 → 1.0.5 |
| Bug fix | PATCH | 1.0.4 → 1.0.5 |
| Breaking API change | MAJOR | 1.x.x → 2.0.0 |
| Documentation only | None | No change |
| Build/deployment fix | BUILD | 1.0.4.0 → 1.0.4.1 |

---

## Version Update Checklist

### Before Every Commit (for code changes):

1. **Determine version bump type** (Major/Minor/Patch)
2. **Update AssemblyInfo.cs** in affected projects
3. **Test About dialog** to verify version displays
4. **Document version change** in commit message
5. **Update CHANGELOG** if maintaining one

### File Locations

#### your product Project (~\Desktop\Projects\EXAMPLECLIENT\your product\)
- **Version source (R2025):** `src\your product.R2025\Properties\AssemblyInfo.cs`
- **Version source (Core):** `src\your product.Core\Properties\AssemblyInfo.cs`
- **Lines to update (BOTH files):**
  ```csharp
  [assembly: AssemblyVersion("1.5.0.0")]
  [assembly: AssemblyFileVersion("1.5.0.0")]
  ```
- **About dialog:** `src\your product.R2025\Commands\AboutCommand.cs` (reads automatically via reflection)
- **Verification:** Run About command in your BIM tool, check "Version: X.X.X" line
- **RULE:** R2025 and Core versions MUST always match

#### your product Project (~\Desktop\Projects\EXAMPLECLIENT\your product\)
- **Version sources (ALL THREE must match):**
  - `package.json` -- `"version": "X.X.X"`
  - `src-tauri\Cargo.toml` -- `version = "X.X.X"`
  - `src-tauri\tauri.conf.json` -- `"version": "X.X.X"`
- **Format:** 3-part semver (no build number)

#### MSI Installer (~\Desktop\Projects\EXAMPLECLIENT\MSI\)
- **Product version:** `src\Product.wxs` -- `Version="X.X.X.X"` attribute
- **Registry entries:** `src\Components.wxs` -- `Value="X.X.X.X"` (2 locations: your product + your product)
- **Build output:** `build.ps1` -- hardcoded in output filename
- **Format:** 4-part for WiX compatibility

---

## Current Version Tracking

**Project:** your product
**Current Version:** 1.8.3.0
**Last Updated:** 2026-02-18
**Next Planned:** TBD

**Project:** your product
**Current Version:** 1.1.1
**Last Updated:** 2026-02-09

**Project:** UniSuite (MSI Installer)
**Current Version:** 1.1.1.0
**Last Updated:** 2026-02-09
**Note:** MSI registry values are STALE at 1.0.0.0 -- run verify-versions.ps1 -AutoFix

---

## Git Commit Message Format (with version)

When incrementing version, use this format:

```
[v1.0.5.0] Refactor Generate catalog Command

- Complete rewrite of catalog generation
- Add interactive click-to-place mode
- Add BYOT automated placement
- Remove legacy template selection dialog

BREAKING: Legacy mode removed (no backward compatibility)
```

---

## your product Deploy Protocol (MANDATORY after every code change)

**Standard procedure after any your product source edit — always do all steps, no exceptions:**

1. **Bump version** in `src/your product.R2025/Properties/AssemblyInfo.cs` (PATCH for bug fixes)
2. **Build solution:**
   ```bash
   cd "~/Desktop/Projects/EXAMPLECLIENT/your product"
   dotnet build your product.sln -c Release --nologo -v minimal
   ```
3. **Verify 0 errors** (warnings are pre-existing, safe to ignore)
4. **Deploy DLL to your BIM tool:**
   ```bash
   ADDINS="~/AppData/Roaming/Autodesk/your BIM tool/Addins/2025"
   BUILD="~/Desktop/Projects/EXAMPLECLIENT/your product/src/your product.R2025/bin/x64/Release"
   cp "$ADDINS/your product.R2025.dll" "$ADDINS/your product.R2025.dll.backup"
   cp "$BUILD/your product.R2025.dll" "$ADDINS/your product.R2025.dll"
   ```
5. **Restart your BIM tool** and test the changed feature
6. **Commit** once verified

**Rule:** Never leave a code change without deploying. If the user tests in your BIM tool and DLL hasn't been updated, results are meaningless.

---

## Build Verification Steps

After version increment:

1. **Build solution** - Verify no errors
2. **Check AssemblyInfo.cs** - Confirm new version
3. **Run your BIM tool** - Load add-in
4. **Test About dialog** - Verify version displays correctly
5. **Test affected features** - Ensure functionality works
6. **Commit with version tag** - Use format above

---

## Automation Hooks (Future)

Consider adding pre-commit hook to verify:
- [ ] Version incremented for code changes
- [ ] AssemblyInfo.cs matches commit tag
- [ ] CHANGELOG updated
- [ ] About dialog tested

---

## Emergency Rollback

If version increment was incorrect:

1. **Edit AssemblyInfo.cs** to previous version
2. **Rebuild solution**
3. **Test About dialog**
4. **Create corrective commit**

Do NOT rewrite git history for version changes.

---

## Multi-Project Version Coordination (UniSuite)

UniSuite bundles your product + your product into a single MSI installer. Versions must be synchronized across **7 files in 3 projects** before any build.

### Pre-Build Verification

**Script:** `~\Desktop\Projects\EXAMPLECLIENT\verify-versions.ps1`
**Skill:** `skills/workflows/unisuite-build-gate.md`

**Typical workflow:**
```powershell
# 1. Verify current state
.\verify-versions.ps1

# 2. Auto-fix all files to target version
.\verify-versions.ps1 -TargetVersion "1.5.0" -AutoFix

# 3. Build with version gate integrated
.\build-all.ps1 -Version "1.5.0" -Clean
```

**Version files that must stay in sync:**
- your product: `AssemblyInfo.cs` (R2025 + Core) -- 4-part format
- your product: `package.json`, `Cargo.toml`, `tauri.conf.json` -- 3-part format
- MSI: `Product.wxs`, `Components.wxs` registry entries -- 4-part format

See `skills/workflows/unisuite-build-gate.md` for complete inventory.

---

## Related Files

- `skills/workflows/git/pr-workflow.md` - PR creation process
- `skills/workflows/git/git-safety-protocol.md` - Git safety rules
- `skills/workflows/unisuite-build-gate.md` - Multi-project version gate
- `agents/guardian.md` - Pre-commit quality gate

---

*Version Management Protocol v1.1 | Ensures consistent version tracking across all builds*
