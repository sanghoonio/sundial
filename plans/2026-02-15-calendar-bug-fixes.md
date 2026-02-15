---
date: 2026-02-15
status: complete
description: Fix three calendar bugs - all-day display, recurring instance editing, dashboard date boundary
---

# Calendar Bug Fixes

## Context

Three interrelated calendar bugs:
1. **Tomorrow's events show on today's dashboard** - All-day events stored at midnight UTC fall within the wrong local-day window
2. **Can't save changes to recurring event instances** - Virtual instances have synthetic IDs that don't exist in DB, so PUT returns 404
3. **Custom events appearing as full-day** - Symptom of #2 (can't toggle off `all_day` on recurring instances) plus missing `original_timezone` on locally-created events

---

## Bug 1: Dashboard date boundary for all-day events

**Root cause** (`api/routes/dashboard.py:99-106`): Events filtered by `start_time >= today_start AND start_time < today_end` where boundaries are local midnight→UTC. For EST (UTC-5), today Feb 15 = `[Feb 15 05:00Z, Feb 16 05:00Z)`. An all-day event for Feb 16 stored at `2026-02-16T00:00:00Z` (from MCP or CalDAV) falls within this range. Additionally, RRULE expansion uses `inc=True` (inclusive both ends) at line 157.

**Fix in `api/routes/dashboard.py`:**
- Split non-recurring event query into two: all-day and timed
- All-day: widen SQL range by +-1 day, then filter in Python by comparing the event's date (converted to user's timezone) to `local_date`
- RRULE expansion: for all-day masters, filter expanded occurrences by date match in user's timezone; for timed events, exclude occurrences `>= today_end`
- Same approach for exception instance queries

---

## Bug 2: Can't edit recurring event instances → edit master instead

**Root cause** (`EventPanel.svelte:111`): Virtual instances have synthetic IDs like `{master_id}__rec__{timestamp}`. Panel sets `liveEventId = event.id` and PUTs to that → 404.

**Approach:** When clicking a virtual instance, fetch the **master** event from the API and load the panel/modal with the master's data. All edits (time, title, all_day, recurrence/termination) save to the master, updating the entire series. This also reveals the RecurrenceInput (currently hidden for instances), giving the user access to the termination date editor.

**Frontend changes:**

`EventPanel.svelte`:
- In the init `$effect`, detect `__rec__` in `event.id`
- Extract master ID from `event.recurring_event_id` or by splitting the synthetic ID
- In the init `$effect`, detect `__rec__` in `event.id`
- Extract master ID from `event.recurring_event_id` or by splitting the synthetic ID
- Fetch `GET /api/calendar/events/{masterId}`
- Initialize form with master's data; set `liveEventId = master.id`
- Add `editingAsSeries` flag → show "Editing recurring series" badge, show RecurrenceInput, show "Delete series" button
- `isRecurringInstance` derived becomes false when `editingAsSeries` is true (so RecurrenceInput renders)

`EventModal.svelte`:
- Same fetch-master logic in the `$effect` that resets form when modal opens
- Saves go to master ID

`ui/src/routes/calendar/+page.svelte`:
- In `handleEventSaved`: trigger `loadData()` when `evt.recurring_event_id` is set (currently only reloads for `evt.rrule`)

---

## Bug 3: Missing `original_timezone` on locally-created events

**Root cause** (`api/routes/calendar.py:134-143`): Locally-created events never set `original_timezone`, so RRULE expansion falls back to UTC.

**Fix:**
- `api/schemas/calendar.py`: Add `original_timezone: str | None = None` to `EventCreate`
- `api/routes/calendar.py:create_event`: Save `body.original_timezone` on the CalendarEvent
- `EventPanel.svelte` + `EventModal.svelte`: Include `Intl.DateTimeFormat().resolvedOptions().timeZone` in create payloads
- `ui/src/lib/types.ts`: Add `original_timezone?: string` to `EventCreate`

---

## Files to modify

| File | Changes |
|------|---------|
| `api/schemas/calendar.py` | Add `original_timezone` to EventCreate |
| `api/routes/calendar.py` | Save `original_timezone` on create |
| `api/routes/dashboard.py` | Split all-day/timed queries; fix RRULE expansion boundaries |
| `ui/src/lib/types.ts` | Add `original_timezone` to EventCreate |
| `ui/src/lib/components/calendar/EventPanel.svelte` | Fetch master for virtual instances; `editingAsSeries` flag; show RecurrenceInput |
| `ui/src/lib/components/calendar/EventModal.svelte` | Same fetch-master logic |
| `ui/src/routes/calendar/+page.svelte` | Reload on recurring-related saves |

## Verification

1. Create a timed recurring daily event in the UI calendar - verify instances show correct times
2. Click a recurring instance → verify panel loads master data with RecurrenceInput visible
3. Change the time on a recurring instance → verify all instances update
4. Set a termination date (UNTIL) on a recurring event → verify it stops generating instances after that date
5. Create an all-day event for tomorrow via MCP → verify it does NOT appear on today's dashboard
6. Create an all-day event for today via MCP → verify it DOES appear on today's dashboard
