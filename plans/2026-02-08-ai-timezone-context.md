# Pass User Timezone to AI Endpoints

## Problem

AI endpoints send UTC timestamps to the LLM with no timezone context. The LLM may reference the wrong day for users not in UTC (e.g., an event at 10pm UTC on Feb 8 is actually Feb 9 in UTC+9). Additionally, `DailySuggestions.svelte` didn't pass `?tz=` to the endpoint.

## Implementation Log

### Changes Made

1. **`ui/src/lib/components/dashboard/DailySuggestions.svelte`** — `loadSuggestions()` now appends `?tz=<IANA>` using `Intl.DateTimeFormat().resolvedOptions().timeZone`, matching the pattern already used in `+page.svelte`.

2. **`api/routes/ai.py`** — In `daily_suggestions()`:
   - Captures `local_date` from `resolve_today(tz)` (was previously discarded with `_`)
   - Resolves user timezone via `zoneinfo.ZoneInfo(tz)` for display conversion
   - Converts event `start_time`/`end_time` and task `due_date` from UTC to the user's local timezone using `.replace(tzinfo=timezone.utc).astimezone(user_tz).isoformat()`
   - Passes `tz` and `local_date` to `ai_service.daily_suggestions()`

3. **`api/services/ai_service.py`** — `daily_suggestions()` now accepts `tz` and `local_date` params. When `local_date` is provided, prepends `"Today is {local_date} ({tz})."` to the context sent to the LLM.

### Backward Compatibility

Both new params (`tz`, `local_date`) default to `None`, preserving existing behavior for callers that don't send them.
