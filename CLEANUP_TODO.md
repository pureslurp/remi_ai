# Cleanup TODO

Action items for you (Sean) following the production debugging session.
Backend code is already cleaned up — these are the things that need to happen
*outside* the codebase (Railway, GCP, Supabase, Cursor MCP).

---

## 1. Rotate leaked credentials (HIGH PRIORITY)

The contents of `.env` were pasted into chat. Rotate everything that grants
access to a real system. Local `.env` and Railway env vars both need to be
updated after each rotation.

- [ ] **Supabase database password** — exposed value: `YgTIIHCLu52HbSa4`
  - Supabase Dashboard → Project `iqdgmhpvycsufqsxqgtu` → **Project Settings → Database → Reset database password**
  - Update `DATABASE_URL` in Railway env vars (the new password also goes into the Supavisor pooler URL)
  - Update `DATABASE_URL` and `SUPABASE_PASSWORD` in your local `.env`
  - Redeploy Railway

- [ ] **Google OAuth client secret** — exposed value: `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`
  - GCP Console → APIs & Services → Credentials → your OAuth 2.0 Client → **Reset secret**
  - Update `GOOGLE_CLIENT_SECRET` in Railway env vars
  - Update `GOOGLE_CLIENT_SECRET` in local `.env`
  - Redeploy Railway

- [ ] **Session secret** — exposed value: `A65y7ZL1Bi78KH6yg5IyBinC1FjRSzzjWNuTF+cn7JLF70k+X50cn+w1whxSJWnE`
  - Generate a fresh long random string: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`
  - Update `SESSION_SECRET` in Railway env vars
  - Update `SESSION_SECRET` in local `.env`
  - Redeploy Railway
  - (Side effect: every existing session is invalidated; you'll have to re-login. That's the desired behavior.)

- [ ] **Anthropic API key** — also pasted; rotate at console.anthropic.com → API Keys → Revoke + new key.
  Update `ANTHROPIC_API_KEY` on Railway and locally.

- [ ] (Optional) Audit recent activity in each provider's dashboard for any sign of the keys having been used by someone else.

---

## 2. Fix `SUPABASE_URL` in `.env`

Your local `.env` currently has:

```
SUPABASE_URL=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...   # this is a JWT, not a URL
```

It should be the project URL. Both local `.env` and Railway env vars need this:

```
SUPABASE_URL=https://iqdgmhpvycsufqsxqgtu.supabase.co
```

Without this, Supabase Storage (document uploads) will fail at runtime because the
storage client builds requests against `SUPABASE_URL`.

- [ ] Fix `SUPABASE_URL` in local `.env`
- [ ] Fix `SUPABASE_URL` in Railway env vars
- [ ] Redeploy Railway
- [ ] Test a document upload to confirm Supabase Storage works

---

## 3. Reconnect the Supabase MCP to the right project

The Supabase MCP in Cursor is currently bound to project `oxgonfjfqicvnzsakxcx`,
not your production project `iqdgmhpvycsufqsxqgtu`. That's why MCP queries failed
during the debugging session and we had to fall back to direct SQL.

- [ ] Cursor → Settings → MCP → reconfigure the `user-supabase` server to point at
      project `iqdgmhpvycsufqsxqgtu` (or run the Supabase MCP installer again with
      the correct project ref).
- [ ] Confirm with a quick SELECT once it's reconnected, e.g. ask the assistant to
      run `SELECT count(*) FROM projects;` via MCP.

---

## 4. Verify `CORS_ORIGIN_REGEX` on Railway

Earlier you set `CORS_ORIGIN_REGEX` on Railway to a value that wasn't valid
Python regex (most likely something with a leading `*`), which crashed every
request with `re.error: nothing to repeat at position 0`.

The backend now validates the regex at startup and ignores invalid values
(logging an error), so this can't take you down again. But still:

- [ ] Railway → Variables → either **delete `CORS_ORIGIN_REGEX`** entirely (if your
      `CORS_ORIGINS` list already covers all origins you care about), **or set a
      valid Python regex** to also match Vercel preview URLs, e.g.:
      ```
      CORS_ORIGIN_REGEX=^https://remi-ai[-\w]*\.vercel\.app$
      ```

---

## 5. Confirm production is healthy after redeploy

Once Railway picks up the cleanup commit:

- [ ] `curl https://remiai-production.up.railway.app/api/health` returns 200 with
      `db_init_ok: true`.
- [ ] Logging into the app shows your 2 projects (already migrated to your real
      Google account on Apr 19 — see `accounts.id = 102141322610175705395`).
- [ ] `POST /api/auth/google/disconnect` from the UI returns 204 (no 500).
- [ ] Gmail sync and Drive sync still work without re-connecting Google
      (the OAuth credential row was migrated from `'legacy'` to your account).

---

## 6. Optional: turn off `REMIP_DEBUG` on Railway

`REMIP_DEBUG=1` makes `/api/health` reveal extra config (CORS list, presence of
secrets as booleans, db init details). Useful while we were debugging; not
needed in steady state. The `/api/debug/db` endpoint that depended on this flag
has been removed from the codebase, so the flag now only affects `/api/health`'s
verbosity.

- [ ] Railway → Variables → delete `REMIP_DEBUG` (or set it to `0`).

---

## What got cleaned up in code (no action needed)

For your records, the following debug surfaces were removed from the backend
in the same commit as this TODO file:

- `GET /api/debug/db` — DB introspection endpoint (used to confirm the
  `'legacy'`-owned data; no longer needed).
- `POST /api/auth/me/claim-legacy` — one-shot data recovery endpoint (you
  already executed the equivalent SQL directly; no longer needed).
- `MIGRATION_DATABASE_URL` env var support — separate connection for Alembic;
  was an escape hatch for Supavisor advisory-lock hangs that turned out not to
  be the issue. The `.env.example` reference was removed.
- The `lock_timeout` / `statement_timeout` SET commands that were wired into
  the migration bootstrap. They were applied to a side connection and never
  reached Alembic's own session, so they did nothing — removed for clarity.

Things that stayed (they're load-bearing, don't remove them):

- `disable_existing_loggers=False` in `backend/alembic/env.py` (without this,
  every log line after migrations is silently suppressed — the original cause
  of "Will assume transactional DDL" looking like a hang).
- `try/except` around `command.upgrade(...)` in `backend/main.py` so a bad
  migration surfaces via `/api/health` instead of killing uvicorn.
- `_bootstrap_postgres()` / `_bootstrap_sqlite()` split + `DB_INIT_STATUS`.
- `SystemExit` for missing `SESSION_SECRET` was downgraded to `logger.error`.
- `CORS_ORIGIN_REGEX` is now validated at startup in `backend/config.py` and
  ignored if it's invalid (logged loudly).
- `require_account` is `async def` so the per-request account ContextVar
  actually propagates to the route handler (was the cause of every authed
  endpoint other than `/google/status` returning 500).
- `bind_request_account_id` / `reset_request_account_id` no longer use the
  `ContextVar.Token` mechanism (was crashing with "Token created in a
  different Context" under FastAPI's threadpool).
- `request.state.account_id` is set as a belt-and-suspenders explicit channel
  alongside the ContextVar.
