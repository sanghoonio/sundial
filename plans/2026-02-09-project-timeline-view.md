# Plan: Project Timeline View

## Context

The projects page currently shows projects as a grid of square cards. The user wants an alternate "timeline" view where each project becomes a full-width row with tasks and notes plotted along a horizontal time axis. This gives a high-level view of project activity over time — something the grid view doesn't communicate at all.

Toggle between grid and timeline using a toolbar button matching the tasks page "Completed" toggle pattern.

## Files

### Modify: `ui/src/routes/projects/+page.svelte`
- Add viewMode state ('grid' | 'timeline')
- Add toggle button in toolbar
- Conditionally render grid vs ProjectTimeline component

### Create: `ui/src/lib/components/projects/ProjectTimeline.svelte`
- Fetch all tasks and notes (2 API calls)
- Group by project_id
- Render rows with horizontal time axis
- Task/note dots positioned by date
- Tooltips, click navigation, responsive layout
