# Plan: Tasks Sidebar + Projects Master-Detail Redesign

## Architecture

```
/tasks              → redirect to /tasks/[first-project]
/tasks/[projectId]  → collapsible project sidebar + kanban board

/projects           → visual card grid (no project selected)
/projects/[id]      → card grid + settings panel (master-detail)
```

- **Tasks page**: Work mode. Collapsible sidebar for project switching, full-width kanban.
- **Projects page**: Manage mode. Visual launchpad card grid. Clicking a card opens settings panel on the right (master-detail via layout, same pattern as notes list + editor).

---

## Implementation Log

### Part 1: Collapsible Project Sidebar on Tasks Page

**File:** `ui/src/routes/tasks/[projectId]/+page.svelte`

- Replaced `FolderKanban` dropdown project selector with a collapsible left sidebar
- Added `PanelLeft`, `Search`, `X` lucide icons
- Added `sidebarOpen` state (default false), `sidebarSearch` for filtering projects
- Added `filteredProjects` derived state for search filtering
- Sidebar uses `transition-[width] duration-200` with `style:width` toggle between `16rem` and `0`
- Inner `w-64` div contains search input + scrollable project list with color dots
- Active project highlighted with `bg-base-300 font-medium`
- Toolbar shows `PanelLeft` toggle button (with `btn-active` when open) + current project name/color

### Part 2: Projects Layout (Master-Detail)

**File:** `ui/src/routes/projects/+layout.svelte` (NEW)

- Follows the notes `+layout.svelte` pattern exactly
- Two-pane flex layout: `absolute inset-0 flex overflow-hidden`
- Left pane (`w-80 lg:w-96`): search, status filter badges, scrollable project card list
- Right pane (`flex-1`): `{@render children()}`
- Responsive: left pane hidden on mobile when a project is selected
- Contains the "New Project" modal (moved from old +page.svelte)
- Loads projects + task counts for progress bars on cards
- Exports `refreshProjects()`, `removeProject()`, `updateProject()` for child route use

### Part 3: Redesigned Project Cards

**In layout left pane:**

- Compact card design with colored left border strip (`w-1 self-stretch rounded-full`)
- Project name (bold) + status badge
- Task progress bar with done/total count
- Milestone count icon
- Description (1-line truncated)
- "Open Board" icon button linking to `/tasks/[id]`
- Selected card highlighted with `border-primary/40 shadow-md`

### Part 4: Settings Panel

**File:** `ui/src/routes/projects/[id]/+page.svelte` (REWRITTEN)

- Removed the old two-column layout (main content + settings sidebar)
- Now a single-pane scrollable settings view that fills the right pane
- Header bar: color dot, editable name, save indicator, delete button
- Back arrow only shows on mobile (`md:hidden`)
- Sections: Description, Status + Color (with preset swatches), "Open Board" link, Task Progress, Milestones, Linked Notes, Recent Tasks, Timestamps
- Auto-save with 500ms debounce (same pattern as before)
- Color presets shown as clickable circles

### Part 5: Empty State

**File:** `ui/src/routes/projects/+page.svelte` (SIMPLIFIED)

- Replaced full page with simple centered placeholder: FolderKanban icon + "Select a project" message
- Follows same pattern as notes `+page.svelte`

### Part 6: Link Updates

- All cross-page links verified correct:
  - Search page → `/tasks/{project_id}` (kanban)
  - Calendar page → `/tasks/${project_id}` (kanban)
  - Projects cards → `/projects/{id}` (settings) + `/tasks/{id}` (board)
  - Sidebar navigation → `/tasks` (redirect) and `/projects` (card list)

## Verification Checklist

- [x] `/tasks` → redirects to `/tasks/[first-project]`
- [x] Tasks page: sidebar toggle works, project list shows, clicking switches projects
- [x] Tasks page: sidebar closed → kanban is full width
- [x] `/projects` → shows card grid, no settings panel
- [x] Click a project card → `/projects/[id]`, settings panel appears
- [x] Settings auto-save works (edit name/description/color/status)
- [x] "Open Board" link navigates to `/tasks/[id]`
- [x] Delete project from settings panel works
- [x] Build compiles successfully with no new errors
