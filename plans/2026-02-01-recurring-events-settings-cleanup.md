# Plan: Recurring Events + Calendar Settings Cleanup

## Implementation Log

### Completed Steps

#### 1. DB Model (`api/models/calendar.py`)
- Added `rrule` (Text, nullable), `recurrence_id` (String, nullable), `recurring_event_id` (String, FK to calendar_events.id, ON DELETE CASCADE)
- Added `recurring_event` self-referential relationship and `exceptions` relationship with cascade delete

#### 2. DB Migration (`api/init_db.py`)
- Added ALTER TABLE migration for the three new columns inline in `init_database()` (same pattern as existing caldav_href/etag migration)

#### 3. CalDAV Sync (`api/services/calendar_sync.py`)
- Switched `expand=True` to `expand=False` in `full_sync` date_search call
- Rewrote `_upsert_from_remote` to separate master VEVENT (with RRULE) from exception VEVENTs (with RECURRENCE-ID)
- Master events stored with `rrule` field, external_id = UID
- Exception events stored with `recurrence_id` and `recurring_event_id` linking to master
- Extracted `_parse_vevent_fields()` helper to deduplicate datetime parsing
- Updated `_event_to_vcalendar` to include RRULE via `vRecur.from_ical()`
- Updated `update_remote_event` to update/remove RRULE in remote VCALENDAR

#### 4. Schemas (`api/schemas/calendar.py`)
- Added `rrule: str | None = None` to `EventCreate`, `EventUpdate`
- Added `rrule`, `recurring_event_id`, `recurrence_id` to `EventResponse`
- Added `sync_interval_minutes: int = 0` to `CalendarSettingsResponse` and `CalendarSettingsUpdate`

#### 5. Calendar Routes (`api/routes/calendar.py`)
- Added `python-dateutil` import for `rrulestr`
- Updated `_build_event_response` to include rrule, recurring_event_id, recurrence_id
- Updated `create_event` to accept rrule
- Rewrote `list_events` with RRULE expansion:
  - Queries non-recurring events, recurring masters, and exception instances separately
  - Expands each master's RRULE using dateutil's rrulestr within the date range
  - Generates virtual instance EventResponse objects with synthetic IDs (`{master_id}__rec__{timestamp}`)
  - Exception instances override corresponding virtual instances
  - Sorts and paginates the combined result
- Added `DELETE /events/{id}/series` endpoint: deletes master + all exceptions + CalDAV remote
- Added `PUT /events/{id}/recurrence` endpoint: updates RRULE on master, pushes to CalDAV
- Added `calendar_sync_interval_minutes` to settings load/save/response

#### 6. Dependencies (`api/requirements.txt`)
- Added `python-dateutil>=2.9.0`

#### 7. Frontend Types (`ui/src/lib/types.ts`)
- Added `rrule` to EventCreate, EventUpdate
- Added `rrule`, `recurring_event_id`, `recurrence_id` to EventResponse
- Added `sync_interval_minutes` to CalendarSettingsResponse and CalendarSettingsUpdate

#### 8. RecurrenceInput Component (`ui/src/lib/components/calendar/RecurrenceInput.svelte`)
- New component with frequency select (None/Daily/Weekly/Monthly/Yearly)
- End condition: Never / After N occurrences / On date
- Builds RRULE string from selections
- Parses existing RRULE string to populate fields on load
- Bindable `value` prop

#### 9. EventPanel (`ui/src/lib/components/calendar/EventPanel.svelte`)
- Added RecurrenceInput after location field (hidden for recurring instances)
- Added rrule to form state, snapshot, and save payload
- Added "Part of a recurring series" badge with Repeat icon for instances
- Added "Delete series" button calling `onseriesdeleted`
- Added `onseriesdeleted` prop

#### 10. Calendar Page (`ui/src/routes/calendar/+page.svelte`)
- Added `handleSeriesDeleted` function: calls DELETE /events/{id}/series and removes all related events from local state
- Added periodic sync timer: fetches calendar settings on mount, sets up setInterval at configured frequency
- Passes `onseriesdeleted` to EventPanel

#### 11. Settings UI (`ui/src/routes/settings/+page.svelte`)
- Removed `pl-3 border-l-2 border-base-300 ml-1` vertical line indent
- Reorganized into subsections: Connection, Calendars, Sync Options
- Added sync frequency dropdown (Manual only / 15min / 30min / 1hr / 6hr)
- Moved sync toggle, sync range, sync button, and last sync time into Sync Options section
- Added descriptive text for sync frequency

### Verification
- `npm run build` passes
- Python imports (models, schemas, routes) verified
- python-dateutil already installed in venv
