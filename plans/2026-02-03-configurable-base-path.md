# Configurable Base Path Deployment

Make Sundial deployable at any path (e.g., `/sundial`, `/app`, or root `/`) via environment variable.

## Environment Variable

- `BASE_PATH` - The subpath to deploy at (e.g., `/sundial`). Defaults to empty string for root deployment.
- Frontend uses `PUBLIC_BASE_PATH` (Vite convention for client-exposed env vars)

## Changes Required

### 1. Frontend: SvelteKit Base Path (`ui/svelte.config.js`)

Read `PUBLIC_BASE_PATH` at build time:

```javascript
import adapter from '@sveltejs/adapter-static';

const basePath = process.env.PUBLIC_BASE_PATH || '';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  kit: {
    paths: {
      base: basePath
    },
    adapter: adapter({
      fallback: 'index.html'
    })
  }
};

export default config;
```

### 2. Frontend: API Client (`ui/src/lib/services/api.ts`)

Use SvelteKit's `base` from `$app/paths`:

```typescript
import { base } from '$app/paths';

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  // path comes in as '/api/...' - prefix with base
  const fullPath = `${base}${path}`;
  const res = await fetch(fullPath, { ... });
  ...
}
```

### 3. Frontend: WebSocket (`ui/src/lib/services/websocket.ts`)

Use `base` for WebSocket URL:

```typescript
import { base } from '$app/paths';

function getUrl(): string {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${location.host}${base}/ws`;
}
```

### 4. Backend: Config (`api/config.py`)

Add `BASE_PATH` setting:

```python
class Settings(BaseSettings):
    BASE_PATH: str = ""  # e.g., "/sundial" for subpath deployment
    # ... existing settings
```

### 5. Backend: Route Mounting (`api/main.py`)

Two approaches - recommend **Option A** for cleaner code:

**Option A: Create sub-application and mount at BASE_PATH**

```python
from api.config import settings

# Create the actual API app
api_app = FastAPI(
    title="Sundial",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    ...
)

# Register routes on api_app (not app)
api_app.include_router(auth_router, prefix="/api")
# ... all other routers

# WebSocket on api_app
@api_app.websocket("/ws")
async def websocket_endpoint(...): ...

# Mount MCP on api_app
api_app.mount("/mcp", mcp_app)

# Static file serving on api_app
# ... serve_spa route

# Root app mounts api_app at BASE_PATH
app = FastAPI()
if settings.BASE_PATH:
    app.mount(settings.BASE_PATH, api_app)
else:
    app = api_app  # Use api_app directly when no base path
```

**Option B: Prefix all routes dynamically** (more complex, not recommended)

### 6. Backend: CORS Update (`api/config.py`)

For production, set `CORS_ORIGINS` to include the production domain:

```
CORS_ORIGINS=https://sanghoon.io,http://localhost:5173
```

### 7. Vite Dev Proxy (`ui/vite.config.ts`)

Update proxy to work with base path in development:

```typescript
const basePath = process.env.PUBLIC_BASE_PATH || '';

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  server: {
    proxy: {
      [`${basePath || ''}/api`]: {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path  // Keep path as-is since backend also uses BASE_PATH
      },
      [`${basePath || ''}/ws`]: {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  }
});
```

## Files to Modify

1. `ui/svelte.config.js` - Add dynamic base path
2. `ui/src/lib/services/api.ts` - Import and use `base` from `$app/paths`
3. `ui/src/lib/services/websocket.ts` - Import and use `base` from `$app/paths`
4. `api/config.py` - Add `BASE_PATH` setting
5. `api/main.py` - Mount app at configurable path
6. `ui/vite.config.ts` - Update dev proxy for base path

## Usage

**Development (root path):**
```bash
# No changes needed - defaults to /
cd ui && npm run dev
cd api && python -m uvicorn api.main:app --reload
```

**Production at /sundial:**
```bash
# Build frontend with base path
PUBLIC_BASE_PATH=/sundial npm run build

# Run backend with base path
BASE_PATH=/sundial python -m uvicorn api.main:app
```

**Production at root:**
```bash
# No env vars needed - defaults work
npm run build
python -m uvicorn api.main:app
```

## Verification

1. Build frontend with `PUBLIC_BASE_PATH=/sundial`
2. Start backend with `BASE_PATH=/sundial`
3. Access at `http://localhost:8000/sundial`
4. Verify:
   - Page loads correctly
   - Assets load (check network tab)
   - Login/API calls work
   - WebSocket connects
   - MCP endpoints accessible at `/sundial/mcp`

---

## Implementation Log (2026-02-03)

### Changes Made

1. **`ui/svelte.config.js`** - Added dynamic base path from `PUBLIC_BASE_PATH` env var
2. **`ui/src/lib/services/api.ts`** - Imported `base` from `$app/paths` and prefixed all API requests
3. **`ui/src/lib/services/websocket.ts`** - Imported `base` from `$app/paths` and included in WebSocket URL
4. **`api/config.py`** - Added `BASE_PATH` setting (defaults to empty string)
5. **`api/main.py`** - Refactored to use `api_app` sub-application, mounted at `BASE_PATH` when configured
6. **`ui/vite.config.ts`** - Updated dev proxy to use `PUBLIC_BASE_PATH` for proxy paths
7. **`ui/tsconfig.json`** - Added `"types": ["vite/client", "node"]` to support `process.env` in vite.config.ts

### Testing

- Backend imports verified: `from api.main import app` works
- Frontend type check passes (1 pre-existing error unrelated to this change)
- Dev server should work at root path by default
- Production deployment with base path requires setting both `PUBLIC_BASE_PATH` (frontend build) and `BASE_PATH` (backend runtime)
