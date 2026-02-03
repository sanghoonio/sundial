# Sundial

A self-hosted personal productivity workspace. Works fully offline with optional AI enhancements.

## Features

- **Notes** — Markdown-based with wiki-style `[[linking]]` between documents
- **Tasks** — Kanban board for task management
- **Calendar** — Sync with Google Calendar or Outlook via CalDAV
- **AI Assistant** — Optional Claude integration for note enhancement

## Tech Stack

| Layer    | Technology                     |
|----------|--------------------------------|
| Backend  | Python, FastAPI, SQLAlchemy    |
| Database | SQLite                         |
| Frontend | SvelteKit, Tailwind, DaisyUI   |

## Quick Start

```bash
# Clone and enter directory
git clone <repo-url> sundial
cd sundial

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings (see Configuration below)

# Backend setup
python -m venv .venv
source .venv/bin/activate
uv sync
uvicorn api.main:app --reload

# Frontend setup (new terminal)
cd ui
npm install
npm run dev
```

Visit `http://localhost:5173` (or your configured base path).

## Configuration

Environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (required) | — |
| `DATABASE_URL` | SQLite database path | `sqlite+aiosqlite:///./workspace/sundial.db` |
| `WORKSPACE_DIR` | Markdown files directory | `./workspace` |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | `http://localhost:5173,http://localhost:3000` |
| `BASE_PATH` | Subpath for deployment (e.g., `/sundial`) | empty (root) |
| `ANTHROPIC_API_KEY` | Claude API key (optional) | — |

Generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Development vs Production

**Development** runs two servers:
- Backend: `uvicorn api.main:app --reload` (port 8000)
- Frontend: `npm run dev` (port 5173)

**Production** builds the frontend and serves everything from FastAPI:

```bash
cd ui
PUBLIC_BASE_PATH=/sundial npm run build  # if using base path
# or just: npm run build

# The built files are served automatically by FastAPI
cd ..
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Deployment Notes

### Reverse Proxy

When running behind nginx or similar:

```nginx
location /sundial/ {
    proxy_pass http://localhost:8000/sundial/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

Ensure `BASE_PATH` in `.env` matches your proxy path.

### HTTPS

For remote access, terminate TLS at your reverse proxy. Sundial itself serves HTTP.

### CORS

Update `CORS_ORIGINS` to include your production domain:

```
CORS_ORIGINS=https://yourdomain.com
```

### Backups

Sundial stores all data in two locations:

- `workspace/sundial.db` — SQLite database (tasks, settings, calendar cache)
- `workspace/` — Markdown note files

Back up the entire `workspace/` directory to preserve all data.

## License

MIT
