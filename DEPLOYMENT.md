# Kova — cloud deployment (Supabase + Vercel + API host)

This document describes **manual** setup in Supabase, Vercel, Google Cloud, and your API host (Railway, Render, or Fly.io). The application reads configuration from **environment variables** on the API server and (for the frontend) from Vite `VITE_*` variables on Vercel.

## Do this in order (happy path)

The sections below are numbered **1–5** in the doc. Follow them **in this sequence** the first time:

| Order | Section | What you do |
| ----- | ------- | ------------- |
| **1** | [§1 Supabase](#1-supabase) | Create project → copy **Postgres** URI → create **Storage** bucket (optional but recommended) → you will paste these into Railway in the next step. |
| **2** | [§2 API host](#2-api-host-docker) · [Railway steps](#railway-step-by-step) | **Railway**: new service from this repo, root **`Dockerfile`**, set env vars (at minimum `DATABASE_URL`, `ANTHROPIC_API_KEY`, and Supabase storage vars if you use Storage). Deploy → copy the public **https** URL of the API. |
| **3** | [§3 Google Cloud](#3-google-cloud-web-oauth-for-production) | Create a **Web** OAuth client. You need the **API URL from step 2** for **Authorized redirect URI** (`…/api/auth/google/callback`). Put client ID/secret on **Railway** as `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`, and set `GOOGLE_REDIRECT_URI`, `FRONTEND_ORIGIN`, `CORS_ORIGINS` there too (see §2 table). |
| **4** | [§4 Vercel](#4-vercel-frontend) | Deploy the **`frontend`** folder. Set **`VITE_API_BASE`** to the **same API origin as step 2** (no `/api` suffix). Redeploy after changing env. |
| **5** | [§5 Checklist](#5-go-live-checklist) | Walk through the checklist before relying on production. |

**Why Supabase before Railway:** Railway needs `DATABASE_URL` (and optional storage keys) in its environment — you get those from Supabase first.

**Why Google after Railway:** Google’s redirect URI must match your real API hostname, which you only know after the API is deployed.

**Why Vercel after Railway:** `VITE_API_BASE` must point at that same API URL.

## Architecture

- **Vercel**: hosts the static Vite frontend.
- **Supabase**: Postgres (`DATABASE_URL`) and optional **Storage** for uploaded and synced document files.
- **Railway / Render / Fly.io**: runs the FastAPI backend (`Dockerfile` in the repo root).

The browser talks to the **API** for `/api/*` routes. Choose one of:

1. **Recommended**: set `VITE_API_BASE` on Vercel to your public API origin (e.g. `https://kova-api.railway.app`). The frontend then calls `https://kova-api.railway.app/api/...`. Enable **CORS** on the API for your Vercel URL(s).
2. **Alternative**: add a `rewrites` entry in `frontend/vercel.json` to proxy `/api/*` to your API (replace the placeholder host). Keep `VITE_API_BASE` unset so the app uses same-origin `/api`.

---

## 1. Supabase

1. Create a project at [https://supabase.com](https://supabase.com).
2. **Database**: In the Supabase dashboard, open **Connect** (or **Project Settings → Database**). Copy a connection string:
   - **Railway, Render, and many other hosts:** use **Session pooler** (Supavisor **session mode**), **not** the “direct” `db.*.supabase.co` URL. Direct connections often resolve to **IPv6 only**; Railway commonly has **no outbound IPv6**, which produces `Network is unreachable` when the app (or Alembic) starts. Session pooler uses a hostname like `aws-0-<region>.pooler.supabase.com` on port **5432** and works over **IPv4**.
   - **Local Mac / IPv6-capable network:** the direct URI is fine.
   - Append `?sslmode=require` to the URI if connections fail without it.
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
| `FRONTEND_ORIGIN` | Yes in cloud | Vercel site URL, e.g. `https://kova.vercel.app` (no trailing slash) |
| `CORS_ORIGINS` | Yes in cloud | Comma-separated list of allowed browser origins (include `https://kova.vercel.app` and preview URLs if needed) |
| `SESSION_SECRET` | Yes with Postgres + Google | Long random string used to sign the **`kova_session` HttpOnly cookie** after OAuth. Without it, users cannot stay signed in. The browser must send cookies on API calls (`credentials: 'include'` in the frontend — already enabled). |
| `PORT` | Usually auto | Render/Railway inject this |

**Multi-tenant:** Each Google user gets an `accounts` row (keyed by Google `sub`), their own `projects.owner_id`, and their own `google_oauth_credentials` row. API routes require a valid session cookie except `/api/health`, `/api/auth/google/url`, `/api/auth/google/callback`, and `/api/auth/google/status`.

**Local-style Google** still works: place `credentials.json` under `~/.kova/` and omit `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`; tokens are stored in `google_token.json` on disk. With **Postgres**, tokens are stored in the `google_oauth_credentials` table instead.

Health check: `GET /api/health`.

### Railway (step-by-step)

These steps assume your code is on GitHub (e.g. `your-org/kova`) and you already have **Supabase** credentials from [§1](#1-supabase). Railway’s UI names move occasionally; if something looks different, use the search box in the dashboard.

#### A. Create the service

1. Open [https://railway.app](https://railway.app) and sign in.
2. **New project** → **Deploy from GitHub repo** (connect GitHub if asked).
3. Pick your **`kova`** repository (or whatever you named it).
4. Railway will propose a new **service** from that repo. Confirm it — you should see a build starting.

#### B. Force Docker (repo root `Dockerfile`)

The API image is defined by the **`Dockerfile` in the repository root** (not under `frontend/`).

1. Click your **service** → **Settings** (gear).
2. Under **Build** (or **Source**):
   - **Root directory**: leave **empty** / repo root so Railway sees the root `Dockerfile`.
   - If Railway picked **Nixpacks** instead of Docker: set builder to **Dockerfile** (wording varies: “Dockerfile”, “Use Docker”, or disable auto Nixpacks and select Dockerfile path `/Dockerfile`).
3. **Start command** (if Railway shows it): leave default empty so the image **`CMD`** runs (`uvicorn` already uses `$PORT` from Railway).
4. Save. Open **Deployments** and trigger **Redeploy** if the first build used the wrong builder.

#### C. Add environment variables

1. Service → **Variables** (or **Variables** tab on the project).
2. Add each variable **one per line** (name = value). Start with these **before** relying on Gmail (you can add Google-related vars after §3):

| Name | Value (example / where to get it) |
| ---- | ----------------------------------- |
| `DATABASE_URL` | Supabase → Project Settings → Database → URI (often add `?sslmode=require` at the end if connections fail). |
| `ANTHROPIC_API_KEY` | Same key you use locally (`sk-ant-...`). |
| `SUPABASE_URL` | Supabase → Project Settings → API → **Project URL**. |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API → **service_role** (secret; never put this in Vercel). |
| `SUPABASE_STORAGE_BUCKET` | Bucket name you created (e.g. `project-docs`). |

After you have your **public API URL** (next step) and your **Vercel** URL, add / update:

| Name | Value |
| ---- | ----- |
| `GOOGLE_REDIRECT_URI` | `https://<YOUR-RAILWAY-HOST>/api/auth/google/callback` (must match Google Cloud exactly). |
| `FRONTEND_ORIGIN` | `https://<your-app>.vercel.app` (no trailing slash). |
| `CORS_ORIGINS` | Same as Vercel origin(s), comma-separated if several, e.g. `https://kova.vercel.app,http://localhost:5173`. |
| `GOOGLE_CLIENT_ID` | From Google Cloud Web client (§3). |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Web client (§3). |

Railway injects **`PORT`** automatically — you do **not** need to set it unless something overrides it.

#### D. Public URL and smoke test

Railway’s labels move; the official flow is **public networking** on the **service** (not only the project name). See Railway’s **[Public networking](https://docs.railway.com/guides/public-networking)** doc if the clicks below don’t match your dashboard.

1. **Open the service**, not just the project overview  
   In the **graph/canvas** view, click the **service** that builds from your GitHub repo (the box that shows deploy/build status). The right-hand panel should be about **that** service.

2. **Find the public URL / domain** (try in this order):
   - **Right panel → `Settings` → scroll to `Networking` → `Public networking`** → **`Generate domain`** (or **Add domain** / **Generate service domain**).  
   - Or a top tab on the service: **`Networking`** (then enable public / generate domain).  
   - Or on the service card: a **globe / “Public”** control that opens networking.

3. Copy the **HTTPS** URL Railway shows (often ends in **`.railway.app`**; older deployments sometimes used **`.up.railway.app`**). That hostname is your **API base** — **no** `/api` suffix.

4. Smoke test in a browser: `https://<that-host>/api/health`  
   - Expect: `{"status":"ok"}`.  
   - If you **don’t** see a Networking / Generate domain section: the latest deploy may have **failed** (fix **Deployments → Logs** first), or you’re on **project** settings instead of **service** settings.

5. If it **502**s or crashes after a good deploy, open **Deployments → View logs** (common causes: `DATABASE_URL`, SSL, missing env).

#### E. What you tell Vercel later

Use that same HTTPS origin (the hostname from step **D.3**) as **`VITE_API_BASE`** on Vercel (still **without** `/api`).

#### Common issues

- **GitHub: Railway only lists one repo (or not your repo)** — Railway can only see repos the **GitHub App installation** is allowed to use.
  1. On GitHub: **Settings** (your profile) → **Applications** → **Installed GitHub Apps** (or [github.com/settings/installations](https://github.com/settings/installations)).
  2. Open **Railway** → **Configure**.
  3. Under **Repository access**, choose **All repositories** *or* **Only select repositories** and tick **your repo** (and any org repo you need).
  4. **Save**, then back in Railway: refresh the GitHub repo picker or start **Deploy from GitHub repo** again.
  - **Org-owned repo:** the org may need to **allow Railway** under the org’s **Settings → Third-party access / GitHub Apps** (or an admin must approve the app for that org).
  - **Wrong GitHub user:** Railway account linked to a different GitHub than the one that owns the repo — check Railway **Account settings** → connected identity.
- **No “Networking” / “Generate domain”** — Open the **service** (GitHub deploy box), not project-only settings; ensure the latest **deployment succeeded**; use Railway’s in-dashboard **search** for `networking` or `domain`; see [Public networking](https://docs.railway.com/guides/public-networking). **CLI alternative:** install the [Railway CLI](https://docs.railway.com/develop/cli), run `railway link` in the repo, then `railway domain` to generate a public URL for the linked service.
- **“Connect to Vercel” in Railway** — That integration is mainly for wiring **Railway-hosted databases** (Postgres/Redis/etc.) into **Vercel** as env vars. It does **not** publish your **FastAPI** container or replace **Public networking**. This project’s database lives in **Supabase**; you still need a **public HTTPS URL for the API service** (dashboard Networking or `railway domain`) so the browser can call `/api/...` and so `VITE_API_BASE` has a target.
- **Build: “Dockerfile not found”** — Root directory is not repo root; set service root to the repo root where `Dockerfile` lives.
- **Runtime: database SSL** — append `?sslmode=require` to `DATABASE_URL` (or use Supabase’s connection string that already includes SSL params).
- **Runtime: `Network is unreachable` to `db.*.supabase.co` (IPv6)** — You used the **direct** DB host; switch `DATABASE_URL` to Supabase **Session pooler** (Connect → **Session** / session mode). See §1 step 2 above.
- **Runtime: Alembic / DB errors on boot** — Logs will show SQL errors; confirm `DATABASE_URL` user/password and that Supabase allows connections from “everywhere” / your IP if restricted.
- **CORS errors from the Vercel site** — `CORS_ORIGINS` on Railway must include the **exact** Vercel origin (scheme + host, no path).

---

## 3. Google Cloud (Web OAuth for production)

1. APIs & Services → Credentials → **Create credentials** → **OAuth client ID** → **Web application**.
2. **Authorized JavaScript origins**: your Vercel URL(s), e.g. `https://kova.vercel.app`.
3. **Authorized redirect URIs**: exactly `https://<YOUR_API_HOST>/api/auth/google/callback` (same value as `GOOGLE_REDIRECT_URI`).
4. Put **Client ID** and **Client secret** in the API environment as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
5. **`FRONTEND_ORIGIN` on Railway** (required for a good UX): after Google approves the user, the API sends the browser to `{FRONTEND_ORIGIN}/?google_connected=1`. If `FRONTEND_ORIGIN` is missing, the app uses the dev default **`http://localhost:5173`**, so production users look like “OAuth broke” when they actually land on localhost. Set it to your **Vercel** site origin (no path, no trailing slash), same host you put in `CORS_ORIGINS`.

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
- [ ] `SESSION_SECRET` set (Postgres + Google); redeploy API after adding  
- [ ] Smoke test from a second device: open app, Google connect, one chat, one upload  

---

## Local development (unchanged)

Use `./run.sh` and `.env` with `ANTHROPIC_API_KEY`. Without `DATABASE_URL`, the app uses SQLite under `~/.kova/` and local disk for documents unless Supabase Storage env vars are set.
