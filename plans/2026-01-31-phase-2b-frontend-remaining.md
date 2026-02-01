# Phase 2b: Frontend Remaining Pages

## Summary

Build the remaining Svelte 5 frontend pages deferred from Phase 2a: Calendar, Projects, Search, and Settings. Also update navigation to include all routes.

**Stack:** Same as Phase 2a -- SvelteKit + Svelte 5 (runes) + TypeScript + Tailwind CSS v4 + DaisyUI v5 + Lucide icons

---

## Status: Complete

---

## Implementation Log

### 1. Navigation Updates - Done
- **Sidebar.svelte** -- Added Calendar, Projects, Search links to main nav; added Settings link in footer section
- **MobileNav.svelte** -- Added Calendar and Search to bottom nav (5 items: Home, Notes, Tasks, Calendar, Search)
- **+layout.svelte** -- Updated `pageTitle` mapping to include Calendar, Projects, Project, Search, Settings

### 2. Calendar Page - Done
- `routes/calendar/+page.svelte` -- Month view with event list, new event button, month navigation
- `components/calendar/CalendarGrid.svelte` -- Full month grid with:
  - Previous/next month navigation
  - Weekday headers
  - Day cells showing up to 3 events with "+N more" overflow
  - Today highlight (primary circle)
  - Out-of-month day dimming
  - Click day to create event, click event to edit
- `components/calendar/EventModal.svelte` -- Create/edit event modal with:
  - Title, description, location fields
  - Start/end date and time pickers
  - All-day toggle (hides time pickers)
  - Delete button for existing events
- API integration: `GET /api/calendar/events`, `POST /api/calendar/events`, `PUT /api/calendar/events/{id}`, `DELETE /api/calendar/events/{id}`

### 3. Projects Pages - Done
- `routes/projects/+page.svelte` -- Project list with:
  - Grid of project cards showing name, description, color dot, status badge, task/milestone counts
  - Create project modal (name, ID, description)
  - Empty state with CTA
- `routes/projects/[id]/+page.svelte` -- Project detail with:
  - Breadcrumb back to projects list
  - Project name/description header
  - Full KanbanBoard reuse (same component as tasks page)
  - TaskDetailModal reuse for editing tasks
  - Project settings modal (edit name, description, add/remove milestones)
  - Delete project option
- API integration: `GET /api/projects`, `POST /api/projects`, `GET /api/projects/{id}`, `PUT /api/projects/{id}`, `PUT /api/projects/{id}/milestones`, `DELETE /api/projects/{id}`

### 4. Search Page - Done
- `routes/search/+page.svelte` -- Global search with:
  - Large search input with icon, autofocused
  - Debounced search (300ms)
  - Result cards showing title, snippet, filepath
  - Total result count
  - Empty state and no-results state
  - Links to note detail pages
- API integration: `GET /api/search?q=&limit=`

### 5. Settings Page - Done
- `routes/settings/+page.svelte` -- App settings organized in card sections:
  - **AI Features**: Enable/disable AI, auto-tag toggle, task extraction toggle (sub-options hidden when AI disabled)
  - **Calendar**: Source selector (Google/Outlook/None), sync toggle, manual sync button
  - **Appearance**: Theme selector (Light/Dark), applies immediately via `data-theme`
  - Save button persists all settings at once
- API integration: `GET /api/settings`, `PUT /api/settings`, `POST /api/calendar/sync`

---

## Key Decisions
- Changed CalendarGrid day cells from `<button>` to `<div>` to avoid nested button HTML invalidity
- Used `svelte-ignore` for DaisyUI label patterns and intentional autofocus on search
- Settings page applies theme change immediately via DOM attribute
- Mobile nav limited to 5 items (Home, Notes, Tasks, Calendar, Search); Settings/Projects accessible via sidebar only
- Project detail reuses the same KanbanBoard and TaskDetailModal components from the tasks page

## Build Output
- Production build succeeds with no errors
- Only benign warnings: daisyUI `@property` CSS, intentional autofocus in TaskQuickAdd
