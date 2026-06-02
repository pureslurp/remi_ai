# Manual Changes Required — Reco Rebrand

These steps require action in external platforms and cannot be automated by code changes alone.

---

## Google Cloud (Drive `drive.file` + Picker)

- [ ] OAuth consent screen: remove `drive.readonly`; add `https://www.googleapis.com/auth/drive.file`
- [ ] Create **API key** with HTTP referrer restrictions for production + `http://localhost:5173/*`
- [ ] Set on **Vercel**: `VITE_GOOGLE_API_KEY`, `VITE_GOOGLE_APP_ID` (GCP project number)
- [ ] Reply to Google verification email: **Confirming narrower scopes** (after deploy)
- [ ] Existing users: reconnect Google and re-pick Drive folder per client

---

## Railway

- [ ] Rename service from `remiai-production` → `reco-production`  
  *(Settings → Service Name)*
- [ ] After rename, update `GOOGLE_REDIRECT_URI` env var to new Railway URL  
  e.g. `https://reco-production.up.railway.app/api/auth/google/callback`
- [ ] Update `CORS_ORIGINS` env var on Railway to include the new Vercel URL (see Vercel step)
- [ ] Update any custom domain if one is configured

---

## Vercel

- [ ] Rename project from `remi-ai-theta` → `reco`  
  *(Project Settings → General → Project Name)*
- [ ] After rename, update `FRONTEND_ORIGIN` env var on Railway to new Vercel URL  
  e.g. `https://reco.vercel.app`
- [ ] Update any custom domain if one is configured

---

## Supabase

- [ ] Rename the Supabase project if it is named after the old app  
  *(Project Settings → General → Project Name)*
- [ ] No schema or data changes needed

---

## Local `.env` (after external renames are complete)

Update the following lines in the repo-root `.env`:

```
# Replace remi-ai-theta.vercel.app with your new Vercel URL
CORS_ORIGINS=https://reco.vercel.app,http://localhost:5173

# Uncomment and update these once the Railway service is renamed:
# GOOGLE_REDIRECT_URI=https://reco-production.up.railway.app/api/auth/google/callback
# FRONTEND_ORIGIN=https://reco.vercel.app
```
