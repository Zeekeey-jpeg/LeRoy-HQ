# Routine Cleanup

## Trigger

This skill activates when:
- `"cancel {routine_id}"`
- `"delete routine {routine_id}"`
- `"remove {routine_id}"`

---

## Purpose

Complete lifecycle management for scheduled routines. Deletes routine from ALL 4 locations:
1. Schedule registry (schedule-registry.json)
2. Windows Task Scheduler
3. Memory system (memory/Routines/ → Archive)
4. Execution logs (automation/logs/ → Archive)

**Critical:** NO orphaned files. Clean architecture maintained.

---

## Protocol

### Step 1: Parse Routine ID

Extract routine ID from prompt:
```python
prompt_lower = prompt.lower()

if "cancel" in prompt_lower:
    routine_id = extract_after_keyword(prompt, "cancel")
elif "delete routine" in prompt_lower:
    routine_id = extract_after_keyword(prompt, "delete routine")
elif "remove" in prompt_lower:
    routine_id = extract_after_keyword(prompt, "remove")

routine_id = routine_id.strip()

if not routine_id:
    print("ERROR: No routine ID specified")
    print("Usage: cancel {routine_id}")
    print("Example: cancel weekly-crm-sales")
    print("\nView available routines: 'show scheduled routines'")
    exit()
```

### Step 2: Validate Routine Exists

```python
registry_path = "~/.claude\\skills\\routines\\schedule-registry.json"
registry = load_json(registry_path)
workflow = find_by_id(registry["workflows"], routine_id)

if not workflow:
    print(f"Routine '{routine_id}' not found in registry.")
    print("\nAvailable routines:")
    for w in registry["workflows"]:
        print(f"  • {w['id']}: {w['name']}")
    print("\nView details: 'show scheduled routines'")
    exit()

# Store workflow details for cleanup
routine_name = workflow["name"]
```

### Step 3: Identify All Files & Locations

Scan for all artifacts:
```python
locations = {
    "registry": {
        "path": "skills/routines/schedule-registry.json",
        "exists": True  # Already validated
    },
    "task_scheduler": {
        "task_name": f"Claude\\{slugify(routine_name, capitalize=True)}",
        "exists": check_task_scheduler_exists(task_name)
    },
    "memory": {
        "path": f"~/Projects\\memory\\Routines\\{routine_id}.md",
        "exists": file_exists(memory_path)
    },
    "logs": {
        "pattern": f"automation/logs/{routine_id}-*.log",
        "count": count_matching_files(log_pattern)
    },
    "xml_definition": {
        "path": f"automation/task-definitions/{routine_id}.xml",
        "exists": file_exists(xml_path)
    }
}
```

### Step 4: Display Cleanup Preview

Show user what will be deleted:
```
┌─ CLEANUP PREVIEW ───────────────────────────────────────────────────┐
│                                                                      │
│ Deleting: {routine_id}                                               │
│ Name: {routine_name}                                                 │
│                                                                      │
│ Will remove from:                                                    │
│  {check_icon} Registry (schedule-registry.json)                      │
│  {check_icon} Task Scheduler ({task_name})                           │
│  {check_icon} Memory (memory/Routines/ → Archive)             │
│  {check_icon} Logs ({log_count} files → Archive)                     │
│  {check_icon} XML Definition (task-definitions/{routine_id}.xml)     │
│                                                                      │
│ ⚠️  This action cannot be undone.                                     │
│ ⚠️  Memory and logs will be archived, not deleted.                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

Proceed with deletion? [y/N]:
```

**Check icons:**
```
✓ - Will be removed (exists)
○ - Not found (skip)
```

### Step 5: Confirm Deletion

```python
user_input = input("Proceed? [y/N]: ")

if user_input.lower() not in ["y", "yes"]:
    print("Deletion cancelled. No changes made.")
    exit()
```

### Step 6: Execute Cleanup (Sequential)

Perform cleanup in order, logging each step:

**6.1 Remove from Registry:**
```python
try:
    registry = load_json(registry_path)
    original_count = len(registry["workflows"])

    # Filter out the target workflow
    registry["workflows"] = [w for w in registry["workflows"] if w["id"] != routine_id]

    new_count = len(registry["workflows"])

    if new_count == original_count:
        LOG: WARNING - Workflow not found in registry (already removed?)
    else:
        write_json(registry, registry_path)
        LOG: ✓ Removed from registry ({original_count} → {new_count} workflows)

except Exception as e:
    LOG: ERROR - Failed to update registry: {e}
    # Continue with other deletions
```

**6.2 Delete Task Scheduler Task:**
```python
if locations["task_scheduler"]["exists"]:
    try:
        # Run schtasks command to delete task
        cmd = f'schtasks /Delete /TN "{task_name}" /F'

        result = run_bash(cmd)

        if result.exit_code == 0:
            LOG: ✓ Deleted Task Scheduler task: {task_name}
        else:
            LOG: ERROR - Task deletion failed: {result.stderr}
            # Continue with other deletions

    except Exception as e:
        LOG: ERROR - Failed to delete task: {e}
else:
    LOG: ○ Task Scheduler task not found (skip)
```

**6.3 Archive Memory File:**
```python
if locations["memory"]["exists"]:
    try:
        memory_path = locations["memory"]["path"]
        archive_dir = "~/Projects\\memory\\Archive\\Routines"

        # Create archive directory if needed
        if not dir_exists(archive_dir):
            create_dir(archive_dir)

        # Move file to archive (preserves for historical reference)
        archive_path = f"{archive_dir}\\{routine_id}.md"
        move_file(memory_path, archive_path)

        LOG: ✓ Memory file archived to: {archive_path}

    except Exception as e:
        LOG: ERROR - Failed to archive memory: {e}
else:
    LOG: ○ Memory file not found (skip)
```

**6.4 Archive Log Files:**
```python
if locations["logs"]["count"] > 0:
    try:
        log_pattern = f"automation/logs/{routine_id}-*.log"
        matching_logs = find_files(log_pattern)

        archive_dir = f"automation/logs/archive/{routine_id}"
        create_dir(archive_dir)

        for log_file in matching_logs:
            filename = get_filename(log_file)
            archive_path = f"{archive_dir}/{filename}"
            move_file(log_file, archive_path)

        LOG: ✓ Archived {len(matching_logs)} log files to: {archive_dir}

    except Exception as e:
        LOG: ERROR - Failed to archive logs: {e}
else:
    LOG: ○ No log files found (skip)
```

**6.5 Delete XML Definition:**
```python
if locations["xml_definition"]["exists"]:
    try:
        xml_path = locations["xml_definition"]["path"]
        delete_file(xml_path)
        LOG: ✓ Deleted XML definition: {xml_path}

    except Exception as e:
        LOG: ERROR - Failed to delete XML: {e}
else:
    LOG: ○ XML definition not found (skip)
```

### Step 7: Update Session State

```python
# Update state to reflect deletion
state = load_json("session/state.json")

if "scheduled_execution" in state and state["scheduled_execution"]["routine_id"] == routine_id:
    # Clear current execution if it was this routine
    del state["scheduled_execution"]

write_json(state, "session/state.json")
```

### Step 8: Display Confirmation

```
✅ Routine deleted: {routine_id}

Removed from {success_count} of {total_count} locations:
 ✓ Schedule registry
 ✓ Task Scheduler ({task_name})
 ✓ Memory (archived to: Archive/Routines/)
 ✓ Logs (archived to: automation/logs/archive/{routine_id}/)
 ✓ XML definition

{failure_messages if any}

Memory archived to: memory/Archive/Routines/{routine_id}.md
(Preserved for historical reference)

View remaining routines: "show scheduled routines"
```

---

## Error Handling & Recovery

| Error | Handling |
|-------|----------|
| **Registry write fails** | Log error, continue with other deletions, warn user |
| **Task delete fails** | Log error (task may not exist), continue |
| **Memory archive fails** | Log error, attempt delete instead of move |
| **Log archive fails** | Log error, continue (logs are non-critical) |
| **Partial cleanup** | Display what succeeded, what failed, suggest manual cleanup |

**Philosophy:** Best effort cleanup. Even if one location fails, continue with others to minimize orphaned files.

---

## Safety Features

**1. Confirmation Required:**
- Always require explicit user confirmation
- Display what will be deleted before proceeding
- Default answer is NO

**2. Archive Instead of Delete:**
- Memory files → Moved to Archive/ (preserved)
- Logs → Moved to archive/ subfolder (preserved)
- Only registry entries and Task Scheduler tasks are permanently deleted

**3. Validation:**
- Check routine exists before prompting
- Verify each location before attempting deletion
- Log all operations for audit trail

**4. Non-Destructive Errors:**
- If a deletion fails, log and continue
- Report all failures at end
- Never exit early (complete as much cleanup as possible)

---

## Integration with Dashboard

After cleanup, user can verify with:
```
"show scheduled routines" → Routine no longer appears in list
"details {routine_id}" → "Routine not found"
```

---

## Example Session

```
User: "cancel weekly-crm-sales"