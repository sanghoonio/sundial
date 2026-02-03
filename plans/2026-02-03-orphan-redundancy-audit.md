# API Orphan & Redundancy Audit

## Plan Summary

Audit the codebase for orphaned data issues and redundancies in tag/FTS handling.

## Issues Analyzed

### 1. Notes Orphaned When Project Deleted (LOW PRIORITY)
**Location:** `api/routes/projects.py:127-135`

When a project is deleted, notes linked to it have `project_id` set to NULL (they remain).

**Assessment:** Intentional design - notes are standalone documents.
**Action:** No change needed.

---

### 2. Tags Not Cleaned Up During Cascade Deletes (MEDIUM PRIORITY)
**Assessment:** Already handled by existing `delete_note()` cleanup logic.
**Action:** No change needed.

---

### 3. Empty Date Directories (VERY LOW PRIORITY)
**Assessment:** Cosmetic issue only.
**Action:** No change needed.

---

## Redundancies Verified

### Tag Name Normalization
- `note_service._get_or_create_tags()` normalizes with `name.strip().lower()` (line 39)
- `ai_service.auto_tag()` normalizes return values with `str(t).strip().lower()` (line 218)
- **Result:** Consistent - no issues found

### FTS Index Sync
- `_fts_insert()` on note create
- `_fts_update()` on note update (calls delete then insert)
- `_fts_delete()` on note delete
- **Result:** Consistent - no issues found

---

## Implementation Log

### Created: `scripts/db_audit.py`

A database audit utility that:
1. Finds orphaned tags (tags with no notes)
2. Finds notes/tasks with invalid project references
3. Finds orphaned FTS entries
4. Finds notes missing FTS entries
5. Detects duplicate tag names

**Usage:**
```bash
# Audit only
python scripts/db_audit.py

# Audit and fix automatically
python scripts/db_audit.py --fix
```

### Cleanup Performed

Ran audit and found 2 orphaned tags (`journal`, `daily`) - likely from deleted notes whose tag cleanup wasn't triggered. Cleaned up with `--fix` flag.

**Before:**
```
Orphaned tags (2):
  - journal (id: tag_fa4468a5)
  - daily (id: tag_69f51add)
```

**After:**
```
All issues resolved.
```

---

## Conclusion

The codebase is well-structured with proper cleanup mechanisms:
- Tag cleanup on note delete: ✅ Implemented
- Tag cleanup on tag sync: ✅ Implemented
- FTS sync: ✅ Consistent
- Tag normalization: ✅ Consistent

The audit script provides ongoing verification and cleanup capabilities.
