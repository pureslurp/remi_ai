# REMI AI — cloud deployment (Supabase + Vercel + API host)

This document describes **manual** setup in Supabase, Vercel, Google Cloud, and your API host (Railway, Render, or Fly.io). The application reads configuration from **environment variables** on the API server and (for the frontend) from Vite `VITE_*` variables on Vercel.

## Architecture

- **Vercel**: hosts the static Vite frontend.
- **Supabase**: Postgres (`DATABASE_URL`) and optional **Storage** for uploaded and synced document files.
- **Railway / Render / Fly.io**: runs the FastAPI backend (`Dockerfile` in the repo root).

The browser talks to the **API** for `/api/*` routes. Choose one of:

1. **Recommended**: set `VITE_API_BASE` on Vercel to your public API origin (e.g. `https://remi-api.railway.app`). The frontend then calls `https://remi-api.railway.app/api/...`. Enable **CORS** on the API for your Vercel URL(s).
2. **Alternative**: add a `rewrites` entry in `frontend/vercel.json` to proxy `/api/*` to your API (replace the placeholder host). Keep `VITE_API_BASE` unset so the app uses same-origin `/api`.

---

## 1. Supabase

1. Create a project at [https://supabase.com](https://supabase.com).
2. **Database**: Project Settings → Database → copy the **connection string** (URI). Use the **direct** connection (port `5432`) for a long-running Python container unless Supabase docs recommend the pooler for your plan. Append `?sslmode=require` if the driver requires explicit SSL.
3. Set `DATABASE_URL` on your API host to that URI (never commit it).
4. **Storage** (recommended when the API runs on ephemeral disk):
   - Storage → **New bucket** (e.g. `project-docs`). Prefer **private**; the backend uses the **service role** key to upload/delete.
   - Project Settings → API → copy **Project URL** and **service_role** secret.
5. On the API host set:
   - `SUPABASE_URL` — Project URL  
   - `SUPABASE_SERVICE_ROLE_KEY` — service role key (server only)  
   - `SUPABASE_STORAGE_BUCKET` — bucket name (default in code: `project-docs`)

Run **migrations** automatically: on startup, when `DATABASE_URL` is Postgres, the app runs `alembic upgrade head` (see `backend/main.py`).

---

## 2. API host (Docker)

The repo root `Dockerfile` builds the `backend` package and runs Uvicorn.

Typical env vars:

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `DATABASE_URL` | Yes (cloud) | Supabase Postgres URI |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `SUPABASE_URL` | For Storage | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | For Storage | Service role key |
| `SUPABASE_STORAGE_BUCKET` | No | Defaults to `project-docs` |
| `GOOGLE_CLIENT_ID` | For Gmail/Drive in cloud | Web OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | For Gmail/Drive in cloud | Web OAuth client secret |
| `GOOGLE_REDIRECT_URI` | Yes in cloud | Must match GCP, e.g. `https://YOUR_API/api/auth/google/callback` |
| `FRONTEND_ORIGIN` | Yes in cloud | Vercel site URL, e.g. `https://remi.vercel.app` (no trailing slash) |
| `CORS_ORIGINS` | Yes in cloud | Comma-separated list of allowed browser origins (include `https://remi.vercel.app` and preview URLs if needed) |
| `PORT` | Usually auto | Render/Railway inject this |

**Local-style Google** still works: place `credentials.json` under `~/.remi/` and omit `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`; tokens are stored in `google_token.json` on disk. With **Postgres**, tokens are stored in the `google_oauth_credentials` table instead.

Health check: `GET /api/health`.

---

## 3. Google Cloud (Web OAuth for production)

1. APIs & Services → Credentials → **Create credentials** → **OAuth client ID** → **Web application**.
2. **Authorized JavaScript origins**: your Vercel URL(s), e.g. `https://remi.vercel.app`.
3. **Authorized redirect URIs**: exactly `https://<YOUR_API_HOST>/api/auth/google/callback` (same value as `GOOGLE_REDIRECT_URI`).
4. Put **Client ID** and **Client secret** in the API environment as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

---

## 4. Vercel (frontend)

1. New Project → import this repo.
2. **Root Directory**: `frontend`.
3. Build: `npm run build`, Output: `dist`.
4. **Environment variable**: `VITE_API_BASE` = `https://your-api.example.com` (no trailing slash; do **not** include `/api` — the app appends `/api` itself).

If you use **rewrites** instead, add to `frontend/vercel.json` something like:

```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://your-api.example.com/api/:path*"
    }
  ]
}
```

Then leave `VITE_API_BASE` unset so requests stay same-origin.

---

## 5. Go-live checklist

- [ ] Supabase: database reachable from API; optional Storage bucket created  
- [ ] API: `alembic upgrade head` succeeds (or rely on app startup); secrets only in platform env  
- [ ] Vercel: `VITE_API_BASE` or rewrites correct; production build opens the app  
- [ ] Google: Web client redirect URI matches `GOOGLE_REDIRECT_URI`  
- [ ] CORS: `CORS_ORIGINS` includes your Vercel origin  
- [ ] Smoke test from a second device: open app, Google connect, one chat, one upload  

---

## Local development (unchanged)

Use `./run.sh` and `.env` with `ANTHROPIC_API_KEY`. Without `DATABASE_URL`, the app uses SQLite under `~/.remi/` and local disk for documents unless Supabase Storage env vars are set.
