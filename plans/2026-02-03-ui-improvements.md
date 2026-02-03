# UI Improvements Plan

## Overview
Four UI improvement areas: selection styling, calendar sync button, settings pages cleanup, and sessions location data.

---

## 1. Task/Project Selection Styling

**Goal:** Use light opacity accent color for selected items to make them more distinct.

**New pattern:** `bg-primary/10 border-primary` (light primary tint with primary border)

### Files modified:
- `ui/src/routes/tasks/[projectId]/+page.svelte` - project sidebar selection
- `ui/src/routes/projects/+page.svelte` - project cards selection
- `ui/src/lib/components/tasks/TaskCard.svelte` - task card selection

---

## 2. Calendar Sync Button Relocation

**Goal:** Move sync button from left (next to date label) to right (left of view selector).

**File:** `ui/src/lib/components/calendar/CalendarToolbar.svelte`

**After:** `[Label] | [<] [Today] [>] | [Sync] [Month] [Week] [Day] [Agenda] [+ Event]`

---

## 3. Settings Pages Cleanup

### A. Settings List Pane (match notes styling)
- Sidebar width: `w-56` → `w-72 lg:w-80`
- Content max-width: `max-w-2xl` → `max-w-3xl`

### B. Standardized Dividers
- Use consistent `border-t border-base-300 pt-4 mt-4` pattern across all settings pages

### C. Standardized Gap Sizes
- Use `gap-4` as standard for content containers

### Files modified:
- `ui/src/routes/settings/+layout.svelte`
- `ui/src/routes/settings/account/+page.svelte`
- `ui/src/routes/settings/ai/+page.svelte`
- `ui/src/routes/settings/tokens/+page.svelte`
- `ui/src/routes/settings/data/+page.svelte`

---

## 4. Sessions IP Capture

**Goal:** Store IP address and user agent when tokens are created.

### Backend Changes
- `api/models/settings.py` - Added `ip_address` and `user_agent` columns to AuthToken
- `api/routes/auth.py` - Capture IP and user agent in setup, login, and create_api_key endpoints
- `api/schemas/auth.py` - Added fields to TokenListItem schema
- `api/init_db.py` - Migration to add columns to existing databases

### Frontend Changes
- `ui/src/lib/types.ts` - Added fields to TokenListItem interface
- `ui/src/routes/settings/tokens/+page.svelte` - Display IP and browser info in token list

---

## Implementation Log

**Date:** 2026-02-03

### Completed:
1. Selection styling updated with `bg-primary/10 border-primary` pattern
2. Calendar sync button moved to right section of toolbar
3. Settings pages standardized:
   - Layout sidebar width increased
   - Content max-width increased
   - Gap sizes standardized to gap-4
   - Dividers use consistent border pattern with mt-4
4. IP/User Agent capture implemented:
   - Model columns added
   - Routes capture from Request object with X-Forwarded-For support
   - Schema updated
   - Frontend displays IP and parsed browser name
   - Migration added to init_db.py
