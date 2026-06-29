# TimeFlow Backend

FastAPI + PostgreSQL backend for the TimeFlow prototype.

## Local Development

### 1. Prerequisites
- Python 3.11+
- PostgreSQL (or use Railway's free Postgres add-on locally via a tunnel)

### 2. Install dependencies
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
```
Edit `.env` and fill in:
- `DATABASE_URL` — e.g. `postgresql://user:pass@localhost:5432/timeflow`
- `SECRET_KEY` — any long random string (`python -c "import secrets; print(secrets.token_hex(32))"`)
- `RESEND_API_KEY` — from resend.com (optional; emails are skipped if missing)
- `FRONTEND_URL` — `http://127.0.0.1:5500` for local Live Server

### 4. Run migrations & seed
```bash
alembic upgrade head
python seed.py
```

### 5. Start the server
```bash
uvicorn app.main:app --reload
```

API is live at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

---

## Deploy to Railway

### Step 1 — Create a Railway project
1. Go to [railway.app](https://railway.app) → **New Project**
2. Choose **Deploy from GitHub repo** → connect your repo
3. Select the **`backend/`** folder as the root directory (Railway auto-detects it via `railway.toml`)

### Step 2 — Add PostgreSQL
1. Inside your Railway project, click **+ Add Service** → **Database** → **PostgreSQL**
2. Railway automatically injects `DATABASE_URL` into your backend service — no manual copy needed

### Step 3 — Set environment variables
In your backend service → **Variables** tab, add:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` (7 days) |
| `RESEND_API_KEY` | your key from resend.com |
| `FROM_EMAIL` | `noreply@yourdomain.com` |
| `FRONTEND_URL` | your Vercel URL (add after deploying frontend) |

> **Note:** `DATABASE_URL` is injected automatically by Railway — do **not** set it manually.

### Step 4 — Deploy
Push to GitHub. Railway will:
1. Detect `railway.toml`
2. Run `alembic upgrade head` (migrations)
3. Start `uvicorn app.main:app`

### Step 5 — Seed demo data
After first deploy, open Railway's **shell** tab for your service and run:
```bash
python seed.py
```

### Step 6 — Copy your Railway URL
It looks like `https://timeflow-backend-production.up.railway.app`.
You'll need it for the frontend.

---

## Deploy Frontend to Vercel

### Step 1 — Push the prototype folder
Make sure `vercel.json` is in the root of your repo (it's already there).

### Step 2 — Import to Vercel
1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import your GitHub repo
3. Set **Root Directory** to `/` (the prototype HTML root, not `backend/`)
4. Click **Deploy**

### Step 3 — Wire up the API URL
In each HTML file that needs to call the backend, add at the top of the `<script>` block:

```javascript
const API = "https://your-railway-url.up.railway.app";
```

Then replace any `fetch("/endpoint")` calls with `fetch(API + "/endpoint", { headers: { Authorization: "Bearer " + token } })`.

---

## API Reference

All endpoints return JSON. Authenticated endpoints require:
```
Authorization: Bearer <access_token>
```

You get `access_token` from `POST /auth/login`.

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Get JWT token |
| GET  | `/auth/me` | Current user |

### Timesheets
| Method | Path | Description |
|--------|------|-------------|
| GET  | `/timesheets/?week_start=YYYY-MM-DD` | Get/create my timesheet |
| POST | `/timesheets/entries` | Log a time entry |
| PATCH | `/timesheets/entries/{id}` | Update entry |
| DELETE | `/timesheets/entries/{id}` | Delete entry |
| POST | `/timesheets/{id}/submit` | Submit for approval |
| POST | `/timesheets/{id}/approve` | Approve (manager) |
| POST | `/timesheets/{id}/reject` | Reject (manager) |
| GET  | `/timesheets/team?week_start=YYYY-MM-DD` | Team overview (manager) |

### Allocations
| Method | Path | Description |
|--------|------|-------------|
| GET | `/allocations/me?week_start=YYYY-MM-DD` | My allocations |
| GET | `/allocations/team?week_start=YYYY-MM-DD` | Team allocations (manager) |
| PUT | `/allocations/` | Upsert user+week allocations (manager) |

### Expenses
| Method | Path | Description |
|--------|------|-------------|
| GET  | `/expenses/` | My expenses |
| POST | `/expenses/` | Create expense |
| PATCH | `/expenses/{id}` | Edit draft |
| POST | `/expenses/{id}/submit` | Submit |
| POST | `/expenses/{id}/approve` | Approve (manager) |
| POST | `/expenses/{id}/reject` | Reject (manager) |
| DELETE | `/expenses/{id}` | Delete |
| GET  | `/expenses/team` | Team expenses (manager) |

### Reports (manager only)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/reports/utilization?from_date=&to_date=` | Billable utilization per person |
| GET | `/reports/projects?from_date=&to_date=` | Hours & revenue per project |
| GET | `/reports/expenses?from_date=&to_date=` | Expense summary |

Full interactive docs available at `/docs` once deployed.
