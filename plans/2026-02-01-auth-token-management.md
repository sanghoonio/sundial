# Auth & Token Management System

## Summary

Replace the 24-hour JWT system with no-expiry opaque tokens (`sdl_<random>`). Add a unified token table for browser sessions and API keys. Add account management (username, password change) and token management (list, create API keys, revoke) to the settings page. This lays groundwork for MCP server auth.

---

## Phase 1: Backend Token Infrastructure

### 1. New `AuthToken` model
**File:** `api/models/settings.py`

Add `AuthToken` model alongside `UserSettings`:
- `id` (String PK): `tok_<random_hex>` - non-secret identifier for display/revocation
- `token_hash` (String, unique, indexed): SHA-256 hex of the raw token
- `token_type` (String): `"session"` or `"api_key"`
- `name` (String, nullable): Human label, e.g. "Browser session (2026-02-01)" or "MCP Server"
- `scope` (String): `"read"` or `"read_write"` (default: `"read_write"`)
- `last_used_at` (DateTime, nullable): Updated on each auth check
- `created_at` (DateTime)

### 2. Export from models
**File:** `api/models/__init__.py` - Add `AuthToken` to imports and `__all__`

### 3. Auth utility changes
**File:** `api/utils/auth.py`

- Add `generate_token() -> (raw_token, hash)` using `secrets.token_urlsafe(32)` + `hashlib.sha256`
- Add `hash_token(raw) -> str` helper
- Add `CurrentUser` dataclass with `username`, `token_id`, `scope`, `token_type`
- Update `get_current_user()`:
  - If token starts with `sdl_`: hash it, look up in `auth_tokens`, update `last_used_at`, return `CurrentUser`
  - Otherwise: fall back to JWT decode (backward compat, temporary)
- Keep existing JWT functions for now (remove in Phase 4)

### 4. Update login/setup endpoints
**File:** `api/routes/auth.py`

- `POST /setup`: Create opaque token + store in `auth_tokens`, seed `username=admin` in settings
- `POST /login`: Create opaque token + store in `auth_tokens`
- `GET /me`: Read username from `user_settings` instead of hardcoding "admin"

### 5. New schemas
**File:** `api/schemas/auth.py`

Add: `PasswordChangeRequest`, `UsernameChangeRequest`, `CreateApiKeyRequest`, `TokenListItem`, `ApiKeyCreatedResponse`

### 6. Seed default username
**File:** `api/init_db.py` - Add `("username", "admin")` to the default settings seed loop

---

## Phase 2: New Backend Endpoints

**File:** `api/routes/auth.py`

| Endpoint | Description |
|---|---|
| `PUT /auth/username` | Change username (stored in `user_settings`) |
| `PUT /auth/password` | Change password. Revokes all tokens except current session. |
| `GET /auth/tokens` | List all tokens with `is_current` flag |
| `POST /auth/tokens` | Create API key (returns raw token once) |
| `DELETE /auth/tokens/{id}` | Revoke a token (rejects revoking current session) |
| `DELETE /auth/logout` | Revoke current session token, return 200 |

Key behavior:
- Password change revokes all other sessions/keys
- Cannot revoke your own current session via the tokens endpoint
- Logout explicitly deletes the current token from DB

---

## Phase 3: Frontend

### Types
**File:** `ui/src/lib/types.ts` - Add `TokenListItem`, `ApiKeyCreatedResponse`, `PasswordChangeRequest`, etc.

### Auth store
**File:** `ui/src/lib/stores/auth.svelte.ts` - Update `logout()` to call `DELETE /auth/logout` before clearing localStorage

### Settings page
**File:** `ui/src/routes/settings/+page.svelte`

Add two new cards at the **top** (before AI Features):

**Account card** (User icon):
- Username text input with Save button
- Password change section: current password, new password, confirm, with inline success/error

**Sessions & API Keys card** (Key icon):
- List of tokens: name, type badge, scope badge, last used, created date
- Current session highlighted with "Current" badge, no revoke button
- Revoke button on each non-current token
- "Create API Key" button opens modal:
  - Name input, scope dropdown (Read & Write / Read Only)
  - After creation: shows raw token with copy button + "you won't see this again" warning

---

## Phase 4: Cleanup (deferred)

After 1+ week of the new system running:
- Remove JWT fallback from `get_current_user()`
- Remove `jose` dependency
- Remove `create_access_token()`, `decode_token()`, `ALGORITHM`, `TOKEN_EXPIRY_HOURS`

---

## Files Modified

| File | Changes |
|---|---|
| `api/models/settings.py` | Add `AuthToken` model |
| `api/models/__init__.py` | Export `AuthToken` |
| `api/utils/auth.py` | Token generation, `CurrentUser`, dual-path auth |
| `api/routes/auth.py` | Modified login/setup/me, 5 new endpoints |
| `api/schemas/auth.py` | 5 new Pydantic schemas |
| `api/init_db.py` | Seed default username |
| `ui/src/lib/types.ts` | New TypeScript interfaces |
| `ui/src/lib/stores/auth.svelte.ts` | Server-side logout |
| `ui/src/routes/settings/+page.svelte` | Account + Sessions cards |
