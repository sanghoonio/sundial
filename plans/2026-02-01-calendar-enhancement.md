# Calendar Enhancement Plan

## Context

The calendar is the least developed feature compared to notes (split-pane, block editor, markdown toolbar) and tasks (kanban, filters, inline column management, detail panel). It currently has only a month grid view with basic event CRUD.

**Bug found**: The frontend calls `/api/calendar/events?start_date=...&end_date=...` but the backend expects `?start=...&end=...`. Date filtering is silently broken -- the backend ignores the unknown params and returns all events up to limit=50.

## Plan: 6 Sub-phases

### Sub-phase 1: Bug Fix, Toolbar, and Month View Polish
- Fix `start_date`/`end_date` to `start`/`end`
- Create CalendarToolbar.svelte (navigation, Today, view switcher, New Event)
- Add compact time display on event chips

### Sub-phase 2: Task Due Dates on Calendar
- Add `due_after`/`due_before` query params to backend tasks API
- Create `CalendarItem` union type
- Fetch tasks alongside events, merge, style differently

### Sub-phase 3: Week View
- Create TimeGrid.svelte (shared hourly grid)
- Create WeekView.svelte (7-column layout)
- Create calendar.ts utils

### Sub-phase 4: Day View
- Create DayView.svelte reusing TimeGrid
- Click empty time slot to create event with time pre-filled
- Click day number navigates to day view

### Sub-phase 5: Agenda View
- Create AgendaView.svelte with date-grouped item list

### Sub-phase 6: Mini-Calendar Sidebar and Visual Polish
- Create MiniCalendar.svelte (desktop sidebar)
- Current time indicator, today highlights, color coding

## Implementation Log

All 6 sub-phases completed. Build passes with no errors.

### Files Created
- `ui/src/lib/components/calendar/CalendarToolbar.svelte` -- nav arrows, Today, view switcher (Month|Week|Day|Agenda), New Event button
- `ui/src/lib/components/calendar/WeekView.svelte` -- 7-column week layout with day headers, all-day row, timed events positioned absolutely
- `ui/src/lib/components/calendar/DayView.svelte` -- single-column day view reusing TimeGrid, wider event blocks with time labels
- `ui/src/lib/components/calendar/AgendaView.svelte` -- date-grouped list with Today/Tomorrow labels, time + title + type badge per row
- `ui/src/lib/components/calendar/MiniCalendar.svelte` -- compact month picker in desktop sidebar, dot indicators for dates with items
- `ui/src/lib/components/calendar/TimeGrid.svelte` -- shared hourly grid (24 rows, time labels, hour dividers, current time indicator), scrolls to 7am
- `ui/src/lib/utils/calendar.ts` -- shared date helpers, compact time formatting, item positioning math, overlap layout algorithm

### Files Modified
- `ui/src/routes/calendar/+page.svelte` -- fixed `start_date`/`end_date` bug to `start`/`end`, added view state, toolbar, task fetching, sidebar layout, all 4 view renderers
- `ui/src/lib/components/calendar/CalendarGrid.svelte` -- refactored to accept CalendarItem[], added time display on event chips, task styling (warning/error colors, checkbox icon), day number click handler
- `ui/src/lib/components/calendar/EventModal.svelte` -- added `defaultTime` prop for time slot click pre-fill
- `ui/src/lib/types.ts` -- added `CalendarItem` union type (`type: 'event' | 'task'`)
- `api/routes/tasks.py` -- added `due_after` and `due_before` query params to GET /api/tasks
- `api/services/task_service.py` -- added date range filtering in `list_tasks()`

### Key Decisions
- View state stored in `$state` (not URL params) to avoid reloads
- Tasks and events fetched in parallel via `Promise.all`, merged into `CalendarItem[]` on frontend
- TimeGrid uses CSS Grid with 48px (3rem) hour rows + absolute positioning for events
- Overlap handling via column-packing algorithm in `layoutTimedItems()`
- MiniCalendar hidden on mobile (< lg breakpoint), uses dot indicators for dates with items
- Current time indicator (red line + dot) shown in week/day TimeGrid views
- Today column highlighted with primary/5 background in week view
