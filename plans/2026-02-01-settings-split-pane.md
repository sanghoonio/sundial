# Settings Split-Pane Layout

## Summary

Refactored the settings page from a single scrollable column into a split-pane layout matching the notes page pattern: category list on the left, section content on the right. Each settings category is now its own sub-page with SvelteKit nested routes.

## Categories

| Path | Label | Icon |
|---|---|---|
| `/settings/account` | Account | `User` |
| `/settings/tokens` | Sessions & API Keys | `KeyRound` |
| `/settings/ai` | AI Features | `Bot` |
| `/settings/calendar` | Calendar | `Calendar` |
| `/settings/appearance` | Appearance | `Palette` |
| `/settings/data` | Data | `Database` |

## Files Changed

| File | Action |
|---|---|
| `ui/src/routes/settings/+layout.svelte` | **New** - Split-pane layout with category sidebar |
| `ui/src/routes/settings/+page.svelte` | **Replaced** - Redirects to `/settings/account` |
| `ui/src/routes/settings/account/+page.svelte` | **New** - Username + password change |
| `ui/src/routes/settings/tokens/+page.svelte` | **New** - Token list, revoke, create API key modal |
| `ui/src/routes/settings/ai/+page.svelte` | **New** - AI toggle + sub-toggles, own Save button |
| `ui/src/routes/settings/calendar/+page.svelte` | **New** - Calendar source, CalDAV config, sync options, own Save button |
| `ui/src/routes/settings/appearance/+page.svelte` | **New** - Theme picker, own Save button |
| `ui/src/routes/settings/data/+page.svelte` | **New** - Export/import workspace |

## Implementation Log

- Created `+layout.svelte` with left sidebar (`w-56`) and right content pane, following the notes page `absolute inset-0 flex overflow-hidden` pattern
- Mobile responsive: sidebar hidden when a category is selected (`hidden md:flex` / `flex` toggle based on `hasSelection`)
- Each sub-page has a mobile back button (`ChevronLeft` → `/settings`) visible only on `md:hidden`
- Active sidebar item gets `bg-base-200 font-medium border-l-primary` styling
- Eliminated the global "Save Settings" button — each section (AI, Calendar, Appearance) has its own Save button
- Account and Tokens sections use instant actions (no Save button needed)
- Build passes cleanly with `vite build`
