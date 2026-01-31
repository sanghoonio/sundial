# Phase 1: Backend Alignment with DATABASE.md and BACKEND.md Specs

## Plan

Align the existing backend with the DATABASE.md and BACKEND.md specs. Fix broken FTS5 search, add missing model fields, add missing endpoints, fix response schemas, wire up WebSocket broadcasts, and seed default settings.

AI service and calendar sync remain stubs (Phase 4). No Alembic — DB will be deleted and rebuilt.

### Steps

1. **Model Updates** — Add missing columns to Note, Tag, NoteTag, Project, Task, CalendarEvent, NoteCalendarLink, UserSettings, AIProcessingQueue
2. **Fix init_db.py** — Standalone FTS5 table (no content-sync triggers), seed default settings
3. **FTS5 Manual Sync** — `_fts_insert`/`_fts_update`/`_fts_delete` helpers in note_service
4. **Fix Search Route** — Join on `id` instead of `rowid`, fix snippet column index
5. **New/Updated Schemas** — Align all Pydantic schemas with spec; create `settings.py`, `tag.py`
6. **Update Existing Routes** — Add new fields to responses (notes, projects, tasks, calendar, dashboard)
7. **New Routes** — `GET /api/tags`, `GET/PUT /api/settings`, `GET /api/auth/me`, `POST /api/calendar/sync`, `GET/PUT /api/calendar/settings`, `POST /api/tasks/{id}/checklist`, `POST /api/tasks/{id}/accept`, `GET /api/ai/suggestions/daily`
8. **WebSocket Broadcasts** — `manager.broadcast()` after all mutations
9. **Frontmatter Enrichment** — Pass `linked_tasks`/`linked_events` to `write_note_file()` on update
10. **Rebuild & Verify** — Delete DB, restart, test all endpoints

---

## Implementation Log

### Files Modified (17)

| File | Changes |
|------|---------|
| `api/models/note.py` | Added `Note.is_archived`, `Tag.created_at`, `NoteTag.ai_suggested`, `NoteTag.created_at` |
| `api/models/project.py` | Added `Project.status`, `Project.completed_at` |
| `api/models/task.py` | Added `Task.source_note_id` (FK), `Task.calendar_event_id` (FK), `Task.ai_suggested` |
| `api/models/calendar.py` | Renamed `source` → `calendar_source`, added `calendar_id`, `synced_at`, `NoteCalendarLink.ai_suggested`, `NoteCalendarLink.created_at` |
| `api/models/settings.py` | Added `UserSettings.updated_at`; rewrote `AIProcessingQueue` with `entity_type`/`entity_id`/`operation`/`started_at`/`error_message`, removed `result` |
| `api/init_db.py` | Standalone FTS5 table `fts5(id, title, content, tags)`, removed triggers, seeds `ai_enabled=false` and `calendar_sync_enabled=false` |
| `api/services/note_service.py` | Added `_fts_insert`/`_fts_update`/`_fts_delete` helpers, called from CRUD; eagerly loads `calendar_links`/`incoming_links` in `get_note`; enriches frontmatter with linked tasks/events on update |
| `api/services/task_service.py` | `create_task()` now accepts `source_note_id`, `calendar_event_id` |
| `api/schemas/note.py` | Added `NoteListItem.linked_tasks`/`linked_events`/`preview`; `NoteResponse.linked_notes`/`linked_tasks`/`linked_events`/`is_archived`; `BacklinkTaskItem`, `BacklinksResponse` |
| `api/schemas/project.py` | Added `ProjectResponse.status`/`task_count`; `ProjectUpdate.status` |
| `api/schemas/task.py` | Added `TaskCreate.source_note_id`/`calendar_event_id`; `TaskResponse.source_note_id`/`calendar_event_id`/`ai_suggested` |
| `api/schemas/calendar.py` | Renamed `source` → `calendar_source`, added `calendar_id`/`synced_at`; added `CalendarSettingsResponse`/`CalendarSettingsUpdate` |
| `api/schemas/auth.py` | Added `UserResponse` schema |
| `api/routes/notes.py` | Enriched responses, backlinks returns `BacklinksResponse` (notes + tasks), WebSocket broadcasts |
| `api/routes/tasks.py` | Passes `source_note_id`/`calendar_event_id`, added `/checklist` and `/accept` endpoints, broadcasts |
| `api/routes/projects.py` | Handles `status` update (sets `completed_at`), returns `task_count`, broadcasts |
| `api/routes/calendar.py` | Uses `calendar_source`, added `/sync` stub, `/settings` GET/PUT, broadcasts |
| `api/routes/dashboard.py` | Renamed to spec fields: `date`, `calendar_events`, `tasks_due`, `tasks_linked_to_events`, `suggestions`; limits notes to 7 days |
| `api/routes/ai.py` | Added `GET /ai/suggestions/daily` stub |
| `api/routes/auth.py` | Added `GET /auth/me` |
| `api/main.py` | Registered `tags_router`, `settings_router` |

### Files Created (4)

| File | Purpose |
|------|---------|
| `api/schemas/settings.py` | `SettingsResponse`, `SettingsUpdate` |
| `api/schemas/tag.py` | `TagWithCount`, `TagListResponse` |
| `api/routes/tags.py` | `GET /api/tags` — tags with note counts |
| `api/routes/settings.py` | `GET /api/settings`, `PUT /api/settings` |

### Spec Coverage

| BACKEND.md Endpoint | Status |
|---------------------|--------|
| `POST /api/auth/setup` | Done |
| `POST /api/auth/login` | Done |
| `GET /api/auth/me` | Done (new) |
| `GET /api/notes` | Done (added preview, linked_tasks, linked_events) |
| `POST /api/notes` | Done |
| `GET /api/notes/{id}` | Done (added linked_notes, linked_tasks, linked_events, is_archived) |
| `PUT /api/notes/{id}` | Done |
| `DELETE /api/notes/{id}` | Done |
| `GET /api/notes/{id}/backlinks` | Done (returns notes + tasks) |
| `GET /api/tasks` | Done |
| `POST /api/tasks` | Done (added source_note_id, calendar_event_id) |
| `GET /api/tasks/{id}` | Done |
| `PUT /api/tasks/{id}` | Done |
| `PUT /api/tasks/{id}/move` | Done |
| `POST /api/tasks/{id}/checklist` | Done (new) |
| `POST /api/tasks/{id}/accept` | Done (new) |
| `DELETE /api/tasks/{id}` | Done |
| `GET /api/projects` | Done (added status, task_count) |
| `POST /api/projects` | Done |
| `GET /api/projects/{id}` | Done |
| `PUT /api/projects/{id}` | Done (handles status → completed_at) |
| `PUT /api/projects/{id}/milestones` | Done |
| `DELETE /api/projects/{id}` | Done |
| `GET /api/calendar/events` | Done |
| `POST /api/calendar/events` | Done (calendar_source field) |
| `GET /api/calendar/events/{id}` | Done |
| `PUT /api/calendar/events/{id}` | Done |
| `DELETE /api/calendar/events/{id}` | Done |
| `POST /api/calendar/sync` | Done (stub) |
| `GET /api/calendar/settings` | Done (new) |
| `PUT /api/calendar/settings` | Done (new) |
| `GET /api/search` | Done (fixed FTS5 join + snippet) |
| `GET /api/tags` | Done (new) |
| `GET /api/dashboard/today` | Done (spec-compliant field names) |
| `GET /api/settings` | Done (new) |
| `PUT /api/settings` | Done (new) |
| `POST /api/ai/chat` | Done (stub) |
| `POST /api/ai/analyze-note/{id}` | Done (stub) |
| `GET /api/ai/suggestions/daily` | Done (stub, new) |
| WebSocket broadcasts | Done (note/task/project/event mutations) |

### Not Yet Implemented (Phase 4)

- AI service integration (Claude API calls)
- Calendar sync with Google/Outlook
- Background task processing for AI operations
- AI auto-tagging, task extraction, event linking
