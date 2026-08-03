# Bulk Gmail Mailer

Send personalised HTML emails in bulk via the Gmail API with:
- **Automatic HTML → PowerPoint** attachment generation
- **Auto-rotating sender display names** per email
- **`{{tag}}` template engine** for per-recipient content personalisation
- Built-in rate limiting and dry-run mode

---

## Three ways to use it

- **MailPilot SaaS** (multi-tenant web app) — `python run_saas.py` then open
  http://localhost:5001. Sign up, manage isolated campaigns per account, with
  subscription tiers and usage limits. See [SaaS mode](#mailpilot--saas-mode) below.
- **Single-user Web UI** — `python app.py` then open http://localhost:5000 in your
  browser. Edit settings, templates, and recipients in the page, click buttons to
  preview and send.
- **Command line** — see the `python main.py …` commands further down.

---

## MailPilot — SaaS mode

`saas/` turns the single-user mailer into a hosted, multi-tenant product built on
the same core engine (`src/`). It adds user accounts, per-user data isolation,
subscription tiers with enforced usage quotas, a dashboard, and a marketing site —
with **no extra dependencies** (stdlib `sqlite3` + Flask/werkzeug).

### Easiest way to run (one command)

No Python setup needed — the launcher creates a virtual environment, installs
dependencies, and starts the server. Then open **http://localhost:5001**.

**macOS / Linux**
```bash
./start.sh
```

**Windows** — double-click `start.bat`, or in a terminal:
```bat
start.bat
```

**Docker** (no Python at all)
```bash
docker compose up          # then open http://localhost:5001
# or:  docker build -t mailpilot . && docker run -p 5001:5001 mailpilot
```

Change the port with `PORT=8080 ./start.sh` (or `set PORT=8080` before `start.bat`).

### Manual run

```bash
pip install -r requirements.txt
python run_saas.py            # http://localhost:5001
```

Environment variables:

| Var | Default | Purpose |
|-----|---------|---------|
| `SAAS_SECRET_KEY` | `dev-saas-key-change-me` | Flask session secret — **set this in production** |
| `SAAS_DATABASE`   | `data/saas.db` | SQLite database path |
| `PORT`            | `5001` | Port to bind |

### What you get

- **Accounts** — signup / login / logout, passwords hashed with werkzeug, session auth.
- **Isolated workspaces** — every account's campaigns, recipients, templates, and
  sender settings are scoped by `user_id` at the database layer.
- **Campaigns** — create/edit/delete; each stores a subject template, HTML body,
  recipients CSV, and a PPTX-attachment toggle. Live preview renders any row with
  `{{tag}}` substitution; dry-run validates the whole batch.
- **Plans & quotas** — Free / Pro / Business tiers (`saas/plans.py`). Monthly send
  caps and campaign counts are enforced *before* a send starts; feature gates cover
  sender-name rotation and PPTX attachments. A live usage meter shows sends used.
- **Billing** — a self-serve plan-change flow (demo mode: no card charged). The same
  handler is where Stripe Checkout drops in for production.

### Subscription tiers

| Plan | Price | Emails/mo | Campaigns | Sender rotation | PPTX |
|------|-------|-----------|-----------|-----------------|------|
| Free | $0 | 100 | 2 | — | — |
| Pro | $19 | 5,000 | Unlimited | ✓ | ✓ |
| Business | $49 | 50,000 | Unlimited | ✓ | ✓ |

### Real Gmail delivery

Sends default to a safe **dry-run/simulate** that still counts toward usage so the
meter is honest. Real delivery uses the core Gmail sender: multi-tenant deployments
would add per-user OAuth; for dev/self-host, dropping `config/credentials.json` +
`config/token.json` in place lets `send` deliver through that mailbox (see
`saas/sending.py::get_service_for_user`).

### Layout

```
saas/
├── app.py         # Flask app factory + all routes
├── auth.py        # session auth, login_required, current_user
├── db.py          # sqlite connection + schema bootstrap
├── models.py      # users / campaigns / send-events data access + quota helpers
├── plans.py       # tier definitions, prices, limits
├── sending.py     # per-campaign render + send, quota enforcement
├── templates/     # landing, pricing, auth, dashboard, editor, billing
└── static/saas.css
run_saas.py        # entry point
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a Gmail API credential

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services → Credentials**
2. Create an **OAuth 2.0 Client ID** (Desktop app type)
3. Download the JSON and save it as `config/credentials.json`
4. Enable the **Gmail API** for your project

### 3. Generate starter files

```bash
python main.py init
```

This creates:
- `config/settings.json` — sender config
- `data/recipients.csv` — recipient list with columns for tags
- `templates/subject.txt` — email subject template
- `templates/body.html` — HTML email body template

### 4. Authenticate

```bash
python main.py auth
```

A browser window opens for Google OAuth. The token is saved to `config/token.json`.

### 5a. Launch the web UI

```bash
python app.py
```
Open http://localhost:5000 — edit everything in the page, click **Preview**, **Dry Run**, then **Send**.

### 5b. Or use the CLI — preview before sending

```bash
# Preview how row 1 of recipients.csv will look after tag substitution
python main.py preview --index 1
```

### 6. Send

```bash
# Dry run — prints what would be sent, no actual emails
python main.py send --dry-run

# Real send with HTML→PPT attachment
python main.py send

# Send without PPT attachment (HTML only)
python main.py send --no-pptx
```

---

## Template Tags

Tags are written as `{{tag_name}}` in `templates/subject.txt` and `templates/body.html`.

| Tag | Source | Description |
|-----|--------|-------------|
| `{{first_name}}` | CSV column | Recipient's first name |
| `{{last_name}}` | CSV column | Recipient's last name |
| `{{company}}` | CSV column | Company name |
| `{{position}}` | CSV column | Job title |
| `{{date}}` | Built-in | Today's date, e.g. `May 27, 2026` |
| `{{time}}` | Built-in | Current time, e.g. `14:30` |
| `{{index}}` | Built-in | 1-based row number in this send batch |
| `{{random_id}}` | Built-in | Short random hex string for tracking |

Add any column to `recipients.csv` and reference it as `{{column_name}}` in templates.

List all tags in current templates:

```bash
python main.py tags
```

---

## Sender Name Rotation

In `config/settings.json`, set multiple sender names:

```json
{
  "sender_email": "you@gmail.com",
  "sender_names": ["Alice from Acme", "Bob at Acme", "Acme Team"],
  "delay_seconds": 1.5,
  "max_per_run": 0
}
```

The `sender_names` list cycles round-robin — email 1 uses name 1, email 2 uses name 2, etc.
The `sender_email` stays fixed (your authenticated Gmail address).

---

## HTML → PowerPoint Attachment

When `--no-pptx` is **not** passed, the rendered HTML body is automatically converted to a
`.pptx` file and attached to the email:

- Each `<h1>` / `<h2>` heading starts a new slide
- Paragraphs and list items become slide body text
- Tables are rendered as text rows
- Fully personalised per recipient (tags are resolved before conversion)

---

## Rate Limiting

Gmail's free tier allows ~500 emails/day and ~25 emails/second.
Set `delay_seconds` in `settings.json` to control the pause between sends (default `1.5`).
Use `max_per_run` to cap a single run (e.g. `100` per run).

---

## File Structure

```
MAILER/
├── main.py                  # CLI entry point
├── requirements.txt
├── config/
│   ├── credentials.json     # ← you provide (OAuth secret, gitignored)
│   ├── credentials.sample.json
│   ├── settings.json        # sender config
│   └── token.json           # auto-generated after auth (gitignored)
├── data/
│   └── recipients.csv       # email,first_name,last_name,...
├── templates/
│   ├── subject.txt          # subject line with {{tags}}
│   └── body.html            # HTML body with {{tags}}
└── src/
    ├── auth.py              # Gmail OAuth2
    ├── mailer.py            # bulk send logic
    ├── html_to_ppt.py       # HTML → .pptx converter
    ├── template_engine.py   # {{tag}} renderer
    └── sender_rotator.py    # round-robin sender names
```
