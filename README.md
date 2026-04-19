# REMI AI — Real Estate Michigan AI Assistant

A local AI assistant for Michigan real estate agents. Each client gets a dedicated project workspace with persistent chat, deal tracking, synced Gmail threads, Google Drive documents, and manual file uploads — all grounded in that client's context.

---

## Quick Start

```bash
# 1. Add your Anthropic API key to .env
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" > .env

# 2. Start everything
./run.sh
```

Opens at **http://localhost:5173**

### Cloud (Supabase + Vercel + API host)

For multi-device access, use Postgres and an always-on API. See **[DEPLOYMENT.md](DEPLOYMENT.md)** for Supabase, Vercel, Railway/Render/Fly, Google OAuth (web client), and environment variables.

---

## Setup

### 1. Anthropic API Key

Get your key at https://console.anthropic.com/  
Add it to `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Google Account (for Gmail + Drive sync)

This is a one-time setup. You'll create a free GCP project and give REMI AI read-only access to your Gmail and Drive.

#### Step 1 — Create a GCP Project
1. Go to https://console.cloud.google.com/
2. Click the project dropdown at the top → **New Project**
3. Name it "REMI AI" → **Create**

#### Step 2 — Enable APIs
1. In your new project, go to **APIs & Services → Library**
2. Search for **Gmail API** → Enable
3. Search for **Google Drive API** → Enable

#### Step 3 — Configure OAuth Consent Screen
1. Go to **APIs & Services → OAuth consent screen**
2. Choose **External** → Create
3. Fill in:
   - App name: `REMI AI`
   - User support email: your email
   - Developer contact: your email
4. Click **Save and Continue** through Scopes (skip for now)
5. On **Test users**, click **+ Add Users** → add your Google email → **Save**
6. Click **Back to Dashboard**

#### Step 4 — Create OAuth Credentials
1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth client ID**
3. Application type: **Desktop app** for local `./run.sh` (NOT Web application). For **hosted** REMI, create a separate **Web application** client and follow [DEPLOYMENT.md](DEPLOYMENT.md).
4. Name: `REMI AI Desktop`
5. Click **Create**
6. Click **Download JSON** on the popup
7. Rename the downloaded file to `credentials.json`
8. Move it to `~/.remi/credentials.json`:
   ```bash
   mkdir -p ~/.remi
   mv ~/Downloads/client_secret_*.json ~/.remi/credentials.json
   ```

#### Step 5 — Connect in REMI AI
1. Start REMI AI with `./run.sh`
2. Click **Connect Google** in the yellow banner at the top
3. Sign in with your Google account and accept the permissions
4. You'll be redirected back to REMI AI — the banner will disappear

> **Note:** While the app is in "Testing" mode, Google tokens expire after 7 days. If Gmail/Drive sync stops working, click Connect Google again to reconnect. To remove this limitation, go back to the OAuth consent screen and click **Publish App** (you can keep it External — it just removes the 7-day limit for your own account).

---

## How to Use

### Creating a Client
1. Click **+ New Client** in the left sidebar
2. Enter their name, type (buyer/seller), email address, and phone
3. Add notes about their situation (pre-approval amount, preferences, budget)

### Tracking a Deal
In the right panel under **Active Transaction**:
- Click **+ Add** to create a transaction
- Enter the property address, offer price, and close date
- Add key dates (inspection deadline, finance contingency, appraisal deadline) with the inline form
- Dates within 3 days are highlighted in orange

### Syncing Gmail
1. Add the client's email address(es) in the **Gmail Sync** section
2. Click **Sync Now** — REMI pulls all Gmail threads involving those addresses
3. Email threads (including PDF/DOCX attachments) become part of the AI context

### Syncing Google Drive
1. Open the client's Google Drive folder in your browser
2. Copy the URL (e.g. `https://drive.google.com/drive/folders/1AbCdEfG...`)
3. Paste it in the **Drive Sync** section and press Tab to save
4. Click **Sync Now** — all files (including subfolders) are indexed

### Uploading Documents
- Drag & drop files onto the Documents drop zone, or click to browse
- Supports PDF, DOCX, TXT (up to 20MB each)
- Documents are automatically extracted and added to the AI context

### Chatting with REMI
- Type in the chat box and press Enter
- REMI has access to everything: the client profile, active deal + key dates, all documents, and email threads
- REMI will cite documents and emails by name when referencing them
- Press **Shift+Enter** for a newline in your message
- Click the red stop button to cancel a streaming response

### Drafting Email Replies
After REMI writes a suggested email reply, you can click **Draft Email Reply** at the bottom of the chat to save it as a Gmail draft (not sent). Review and send it from Gmail.

---

## Data & Privacy

- **Local mode** (default): data lives on your machine under `~/.remi/` (SQLite and document files).
- **Cloud mode** (see [DEPLOYMENT.md](DEPLOYMENT.md)): Postgres and optional Supabase Storage replace local SQLite and `projects/.../docs/`; Google tokens are stored in Postgres when using `DATABASE_URL`.
- Nothing is sent to Anthropic except the content you include in chat messages
- Anthropic does not train on API inputs by default
- Your Google OAuth token is stored at `~/.remi/google_token.json` — never committed to git

---

## File Locations

```
~/.remi/
  remi.db              # SQLite database (all clients, messages, deals)
  projects/
    <client-id>/
      docs/            # Uploaded and Gmail-attached documents
  credentials.json     # Google OAuth credentials (you place this)
  google_token.json    # Google OAuth token (auto-created on connect)
  logs/
    remi.log           # Application logs for debugging
```

---

## Troubleshooting

**Gmail/Drive sync shows "token_expired"**  
→ Click **Connect Google** again in the top banner. Tokens expire after 7 days in test mode.

**"credentials.json not found"**  
→ Follow the GCP setup steps above. Make sure the file is at `~/.remi/credentials.json`.

**Backend won't start**  
→ Make sure your `ANTHROPIC_API_KEY` in `.env` starts with `sk-ant-`

**Document not appearing in chat context**  
→ Check `~/.remi/logs/remi.log` for extraction errors. Very large PDFs (100+ pages) may take a moment to process.

---

## Roadmap

- **MLS Integration** — Pull property data from Realcomp II by MLS number
- **Voice Notes** — Whisper transcription for quick dictation between showings
- **Daily Briefing** — "Here's what changed across all active clients since yesterday"
- **Cross-client search** — Search all clients and documents at once
