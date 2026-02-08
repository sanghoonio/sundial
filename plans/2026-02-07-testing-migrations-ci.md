# Plan: Testing, Migrations, Health Check, Backup CLI, and CI

## Context
Sundial currently has no automated tests, no CI pipeline, manual inline migrations in `init_db.py`, and no backup tooling. This plan adds all five requested features to bring the project to production-quality infrastructure.

## Implementation Order
1. Health check endpoint (smallest, no dependencies, tested by later features)
2. Alembic migrations (replaces fragile ALTER TABLE pattern)
3. Backup/restore CLI (standalone, no deps on test infra)
4. Backend tests (pytest)
5. Frontend tests (Vitest)
6. E2E tests (Playwright)
7. GitHub Actions CI (depends on all above)

---

## 1. Health Check Endpoint

**New file:** `api/routes/health.py`
- `GET /api/health` - no auth required
- Returns: `{ status, version, database, uptime_seconds, timestamp }`
- Uses `get_db` dependency for DB connectivity check (`SELECT 1`)
- Module-level `time.monotonic()` for uptime tracking

**Modify:** `api/main.py` - register health router with `/api` prefix

---

## 2. Alembic Database Migrations

**New files:**
- `alembic.ini` - config at project root, `render_as_batch=True` for SQLite
- `alembic/env.py` - async-compatible with `async_engine_from_config`, imports all models via `api.models`, overrides URL from `api.config.settings`
- `alembic/script.py.mako` - standard template
- `alembic/versions/001_initial_schema.py` - baseline migration (pass-through for existing DBs)

**Modify:** `pyproject.toml` - add `alembic>=1.13.0` to dependencies
**Modify:** `api/init_db.py` - remove all inline ALTER TABLE blocks, add Alembic stamp/upgrade call via `run_in_executor` (avoids nested event loop issue since lifespan is async but Alembic's `command.upgrade()` uses `asyncio.run()` internally)

Key: `render_as_batch=True` in env.py is required because SQLite doesn't support most ALTER TABLE operations natively.

---

## 3. Backup/Restore CLI

**New file:** `cli.py` (project root)
- `sundial backup [-o DIR] [-w WORKSPACE]` - creates `sundial_backup_YYYYMMDD_HHMMSS.tar.gz` containing `sundial.db`, `notes/`, `.encryption_key`
- `sundial restore <archive> [-f] [-w WORKSPACE]` - extracts archive to workspace, interactive confirmation before overwrite
- Uses `argparse` (stdlib only, no new deps), path traversal protection on extract
- Standalone script - does not import FastAPI/SQLAlchemy

**Modify:** `pyproject.toml` - add `[project.scripts] sundial = "cli:main"`

---

## 4. Backend Tests (pytest)

**New files:**
- `tests/__init__.py`
- `tests/conftest.py` - core fixtures:
  - `db_engine` - in-memory SQLite (`sqlite+aiosqlite://`), creates schema + FTS5 + task_notes
  - `client` - `httpx.AsyncClient` with `ASGITransport(app=api_app)`, overrides `get_db`
  - `auth_client` - calls `/api/auth/setup` to get real JWT token, sets `Authorization` header
  - `temp_workspace` (autouse) - monkeypatches `settings.WORKSPACE_DIR` to `tmp_path`
- `tests/test_health.py` - status ok, no auth required
- `tests/test_auth.py` - setup, login, wrong password, me endpoint, unauthenticated access
- `tests/test_notes.py` - CRUD, not found, auth required
- `tests/test_tasks.py` - create, list, update status, delete
- `tests/test_projects.py` - create, list, delete, inbox protection

**Modify:** `pyproject.toml` - add `[tool.pytest.ini_options]` with `asyncio_mode = "auto"`, `testpaths = ["tests"]`

---

## 5. Frontend Tests (Vitest)

**New files:**
- `ui/vitest.config.ts` - jsdom environment, svelte plugin, `$app/*` path aliases to mocks
- `ui/src/lib/__mocks__/paths.ts` - `export const base = ''`
- `ui/src/lib/__mocks__/navigation.ts` - stub `goto`, `invalidateAll`
- `ui/src/lib/__mocks__/state.ts` - stub `page`
- `ui/src/lib/utils/__tests__/calendar.test.ts` - formatDateKey, isToday, isSameDay, getWeekDays, formatCompactTime, formatHourLabel
- `ui/src/lib/utils/__tests__/markdown.test.ts` - markdownPreview (strip syntax, truncation, mermaid blocks)

**Modify:** `ui/package.json` - add devDeps (`vitest`, `@testing-library/svelte`, `jsdom`), add scripts (`test`, `test:watch`)

Focus on utility function tests first (pure TypeScript, reliable). Component tests with Svelte 5 snippets are trickier and can be added incrementally.

---

## 6. E2E Tests (Playwright)

**New files:**
- `ui/playwright.config.ts` - two webServer entries (backend :8000, frontend :5173), separate test DB
- `ui/e2e/login.test.ts` - setup flow, login, wrong password
- `ui/e2e/notes.test.ts` - create note flow
- `ui/e2e/dashboard.test.ts` - verify dashboard sections render

**Modify:** `ui/package.json` - add `@playwright/test` devDep, `test:e2e` script

---

## 7. GitHub Actions CI

**New file:** `.github/workflows/ci.yml`
- **lint-python** - `ruff check` + `ruff format --check` (via `astral-sh/setup-uv@v5`)
- **lint-frontend** - `npm run check` (svelte-check)
- **test-python** - `pytest -v` across Python 3.11/3.12/3.13 matrix
- **test-frontend** - `npm test` (vitest)
- **build-frontend** - `npm run build`, upload artifact
- Trigger: push/PR to main
- No Playwright in CI initially (add later once stable)

**Modify:** `pyproject.toml` - add `ruff>=0.9.0` to dev-dependencies, add `[tool.ruff]` config

---

## Files Modified Summary
| File | Changes |
|------|---------|
| `pyproject.toml` | alembic dep, ruff dev dep, pytest config, console_scripts, ruff config |
| `api/main.py` | Register health router |
| `api/init_db.py` | Replace ALTER TABLE blocks with Alembic runner |
| `ui/package.json` | vitest, playwright, testing-library devDeps + scripts |

## Verification
1. `uv run pytest -v` - all backend tests pass
2. `cd ui && npm test` - all vitest tests pass
3. `cd ui && npx playwright test` - E2E tests pass (with servers running)
4. `uv run sundial backup && uv run sundial restore sundial_backup_*.tar.gz -f` - backup/restore round-trip
5. `curl http://localhost:8000/api/health` - returns status ok
6. `uv run alembic current` / `uv run alembic history` - migration tracking works
