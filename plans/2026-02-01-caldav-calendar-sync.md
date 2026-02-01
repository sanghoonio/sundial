# CalDAV/iCloud Calendar Sync

Replace Google/Outlook stubs with working CalDAV sync (covers iCloud, Fastmail, Nextcloud, etc.).

## Approach

User provides CalDAV URL + username + app-specific password in Settings. The `caldav` Python library (synchronous) handles PROPFIND/REPORT/PUT/DELETE, wrapped in `asyncio.to_thread()` for the async backend. Events sync bidirectionally: local changes push to server, remote changes pull into DB.

## Implementation Log

### Phase 1: Dependencies & Config Cleanup
- Added `caldav>=1.4.0`, `icalendar>=6.0.0` to `api/requirements.txt`
- Removed `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` from `api/config.py`
- Updated `.env.example` to remove Google vars, add CalDAV comment

### Phase 2: Model & Schema Changes
- Added `caldav_href` and `etag` columns to `CalendarEvent` model
- Updated `calendar_source` comment to "local, caldav"
- Added ALTER TABLE migration in `init_db.py` (idempotent with try/except)
- Extended schemas: `CalendarSettingsResponse` with CalDAV fields, `CalendarSettingsUpdate` with credential fields, new `CalendarSyncResult` and `CalDAVCalendarInfo`

### Phase 3: CalDAV Sync Service
- Full rewrite of `api/services/calendar_sync.py` with `CalDAVSyncService`:
  - `list_calendars()`: connects to CalDAV server, returns available calendars with names/colors
  - `full_sync()`: bidirectional sync - push local changes, pull remote events, delete stale events
  - `push_single_event()`: create VEVENT and push to first selected calendar
  - `update_remote_event()`: fetch by caldav_href, update VEVENT fields, save
  - `delete_remote_event()`: fetch by caldav_href, delete
- All caldav calls wrapped in `asyncio.to_thread()`
- iCalendar UID -> external_id, resource URL -> caldav_href, ETag -> etag
- All-day detection via DTSTART date vs datetime
- Conflict resolution: server wins on pull

### Phase 4: API Route Changes
- New `GET /calendar/caldav/calendars` endpoint for testing connection
- `POST /calendar/sync` now calls CalDAV full_sync, stores last_sync_at/error
- `GET /calendar/settings` returns CalDAV fields (url, username, has_password, last_sync)
- `PUT /calendar/settings` accepts CalDAV credential fields
- `POST /calendar/events` pushes to CalDAV after local save (non-blocking)
- `PUT /calendar/events/{id}` updates remote event if caldav_href exists (non-blocking)
- `DELETE /calendar/events/{id}` deletes remote event before local delete (non-blocking)

### Phase 5: Frontend Changes
- Added `CalendarSettingsResponse`, `CalendarSettingsUpdate`, `CalendarSyncResult`, `CalDAVCalendarInfo` types to `types.ts`
- Rewrote settings page calendar section:
  - Dropdown: None (local) / CalDAV
  - CalDAV form: server URL, username, app-specific password inputs
  - "Test Connection" button -> lists available calendars with checkboxes
  - Sync range (past/future days) inputs
  - Sync now button with last sync timestamp and error display

### Bug Fixes & Post-Implementation Changes

**iCloud Auth / URL Resolution:**
- `caldav.icloud.com` redirects across hosts (to `pXX-caldav.icloud.com`), stripping auth headers. Added `_resolve_caldav_url()` but it doesn't reliably resolve iCloud redirects.
- Workaround: users enter their direct CalDAV URL (e.g. `https://p147-caldav.icloud.com/USERID/calendars/`). Updated placeholder text to guide users.

**Recurring event deduplication:**
- `expand=True` in `date_search` expands recurring events into instances that all share the same UID. Each instance was overwriting previous ones in the DB.
- Fix: use `UID + RECURRENCE-ID` as `external_id` for expanded recurring instances.

**Push error surfacing:**
- `push_single_event` was returning `{"error": "..."}` but callers only checked for `"href"` key, silently swallowing errors.
- Fix: added checks for `"error"` key and empty results in both `_push_local_changes` and `create_event` route.

**UI: Event edit modal replaced with side panel:**
- Removed `EventModal.svelte`, created `EventPanel.svelte` rendered inline under MiniCalendar in the right sidebar.
- Widened sidebar from `w-56` to `w-64`, adjusted toolbar padding to `lg:pr-68`.

**Autosave with status indicator:**
- EventPanel uses 800ms debounced autosave with snapshot comparison (matching notes editor pattern).
- Save button shows: Save icon → spinner → green Check → idle.
- Panel handles API calls directly (POST for new, PUT for existing via `liveEventId`).
- Parent callbacks changed from `onsave`/`ondelete` to `onsaved(evt, isNew)`/`ondeleted(id)`.

**All-day checkbox bug:**
- The `$effect` for form initialization was re-running on reactivity cycles, resetting `allDay` back to `event.all_day`.
- Fix: added `initEventKey` state guard so the init effect only runs when the event ID actually changes.

### Verification
- `uv pip install` of caldav + icalendar succeeded
- `npm run build` completed with zero errors (only pre-existing a11y warnings)
- CalDAV connection and pull sync verified working with iCloud (using direct URL + app-specific password)
- Recurring event instances now correctly stored as separate records

## Known Issues
- `_resolve_caldav_url` doesn't reliably handle iCloud's cross-host redirects — users must enter direct CalDAV URL
- Push-to-iCloud (creating events in Sundial → iCloud) needs further testing; errors are now surfaced in sync results and backend logs

## Files Modified
| File | Action |
|------|--------|
| `api/requirements.txt` | Added caldav, icalendar |
| `api/config.py` | Removed Google vars |
| `.env.example` | Removed Google vars, added CalDAV comment |
| `api/models/calendar.py` | Added caldav_href, etag columns |
| `api/init_db.py` | Added column migration |
| `api/schemas/calendar.py` | Extended settings, added sync result schema |
| `api/services/calendar_sync.py` | Full rewrite: CalDAVSyncService |
| `api/routes/calendar.py` | Real sync, caldav/calendars endpoint, push-through on CRUD |
| `ui/src/lib/types.ts` | Added calendar settings types |
| `ui/src/routes/settings/+page.svelte` | CalDAV credential form, calendar picker |
| `ui/src/lib/components/calendar/EventPanel.svelte` | New: inline edit panel with autosave |
| `ui/src/routes/calendar/+page.svelte` | Replaced EventModal with EventPanel in sidebar |
| `ui/src/lib/components/calendar/CalendarToolbar.svelte` | Adjusted padding for wider sidebar |
