# PayLedger — Railway Deployment Guide

> **Goal:** Get PayLedger live on Railway with PostgreSQL + Redis, accessible at a public URL with working Swagger docs. No credit card required.

---

## Before You Start — Checklist

Make sure your project has all of these locally before touching Railway:

- [ ] `docker-compose.yml` working locally (`docker compose up` runs clean)
- [ ] CI passing on GitHub (green checkmark on your repo)
- [ ] All env vars documented in `.env.example`
- [ ] `alembic upgrade head` runs without errors
- [ ] At least one test hitting `/docs` or a health endpoint

If any of these are missing, fix them first. Railway deploys what's in your repo — if it's broken locally, it'll be broken there too.

---

## Step 1 — Prepare Your Repo for Railway

Railway does not use `docker-compose.yml` for production. It uses either your `Dockerfile` directly or a `railway.toml` config file. You need to make a few small changes.

### 1.1 — Create a `railway.toml` in your project root

```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

**Note:** Railway injects a `$PORT` env var automatically — you must use it in your start command, not hardcode 8000.

### 1.2 — Update your `Dockerfile` to use `$PORT`

Your current Dockerfile probably has `--port 8000`. Change it:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Remove the CMD line — railway.toml handles this now
```

Or keep the CMD but make it use the env var:
```dockerfile
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### 1.3 — Add a `/health` endpoint to `app/main.py`

Railway pings this to know your app is alive. Without it, Railway might kill your deployment thinking it failed.

```python
# In app/main.py
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "payleger"}
```

### 1.4 — Update `app/config.py` to read all env vars cleanly

Railway injects env vars — your app must read them from the environment, not from a `.env` file (which you never commit).

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ENVIRONMENT: str = "production"

    class Config:
        env_file = ".env"          # used locally only
        env_file_encoding = "utf-8"

settings = Settings()
```

Install pydantic-settings if not already: `pip install pydantic-settings` and add to requirements.txt.

### 1.5 — Handle Alembic migrations on startup

You need migrations to run automatically when Railway deploys. The cleanest way is to run them at app startup.

```python
# app/main.py — add this near the top
from contextlib import asynccontextmanager
from alembic.config import Config
from alembic import command

@asynccontextmanager
async def lifespan(app):
    # Run migrations on startup
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    yield

app = FastAPI(
    title="PayLedger API",
    description="Fintech wallet and transaction API",
    version="1.0.0",
    lifespan=lifespan
)
```

### 1.6 — Commit and push everything to GitHub

```bash
git add .
git commit -m "chore: prepare for Railway deployment"
git push origin main
```

---

## Step 2 — Set Up Railway

### 2.1 — Create your Railway account

1. Go to **https://railway.app**
2. Click **"Start a New Project"**
3. Sign in with **GitHub** (this is important — Railway needs access to your repos)
4. No credit card needed for the Starter plan ($5 free monthly credits)

### 2.2 — Create a new project

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Find and select your PayLedger repository
4. Railway will detect your Dockerfile and start building — **stop it** before it finishes (click "Cancel deploy") because you need to add PostgreSQL and Redis first, otherwise the app will crash on startup trying to connect to databases that don't exist yet

---

## Step 3 — Add PostgreSQL

1. Inside your Railway project, click **"+ New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Railway provisions a Postgres instance in about 30 seconds
4. Click on the Postgres service → go to **"Variables"** tab
5. You'll see `DATABASE_URL` already set — copy this value, you'll need it

**Important:** Railway's Postgres URL uses `postgresql://` scheme. Your async SQLAlchemy needs `postgresql+asyncpg://`. You'll fix this in Step 5.

---

## Step 4 — Add Redis

1. Click **"+ New"** again
2. Select **"Database"** → **"Redis"**
3. Railway provisions Redis in about 20 seconds
4. Click the Redis service → **"Variables"** tab
5. Copy the `REDIS_URL` value

---

## Step 5 — Set Environment Variables on Your API Service

Click on your **API service** (the one from GitHub) → **"Variables"** tab → **"Raw Editor"**

Paste all of these, replacing the values:

```
SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_hex(32))">
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=production
```

For `DATABASE_URL` — Railway gives you something like:
```
postgresql://postgres:password@host:port/railway
```

You need to change `postgresql://` to `postgresql+asyncpg://`:
```
DATABASE_URL=postgresql+asyncpg://postgres:password@host:port/railway
```

For `REDIS_URL` — paste exactly what Railway gave you, it should already work.

**Pro tip:** Railway has a "Reference Variable" feature. Instead of copy-pasting, you can reference the Postgres service's variable directly:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
```

But you still need to manually add the `+asyncpg` to DATABASE_URL — Railway doesn't know your driver preference.

---

## Step 6 — Trigger Deployment

1. Go to your API service → **"Deployments"** tab
2. Click **"Deploy"** (or push a new commit to trigger it automatically)
3. Click on the active deployment to watch the build logs in real time

**What you'll see in logs (healthy deployment):**
```
Building Docker image...
Installing dependencies...
Running migrations...   ← your lifespan function
INFO: Application startup complete.
INFO: Uvicorn running on 0.0.0.0:PORT
```

**Common errors and fixes — read these before panicking:**

| Error in logs | Cause | Fix |
|---|---|---|
| `connection refused` on startup | App started before DB was ready | Add retry logic (see 6.1 below) |
| `asyncpg.exceptions.InvalidCatalogNameError` | Wrong database name in URL | Check DATABASE_URL in Railway variables |
| `ModuleNotFoundError: pydantic_settings` | Missing from requirements.txt | Add `pydantic-settings` to requirements.txt |
| `error: No module named 'app'` | Wrong working directory | Add `WORKDIR /app` to Dockerfile |
| Port binding error | Not using `$PORT` | Fix CMD to use `${PORT:-8000}` |
| `alembic.ini not found` | Alembic config missing | Make sure alembic.ini is committed to repo |

### 6.1 — Add startup retry for database connection

Sometimes Railway starts your app before Postgres is fully ready. Add this to your database.py:

```python
import asyncio
from sqlalchemy.exc import OperationalError

async def wait_for_db(engine, retries=5, delay=3):
    for attempt in range(retries):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            print("Database connection established")
            return
        except OperationalError:
            print(f"DB not ready, attempt {attempt + 1}/{retries}, retrying in {delay}s...")
            await asyncio.sleep(delay)
    raise Exception("Could not connect to database after multiple retries")
```

Call this in your lifespan function before running migrations.

---

## Step 7 — Get Your Public URL

1. Go to your API service → **"Settings"** tab
2. Under **"Networking"** → click **"Generate Domain"**
3. Railway gives you a URL like `payleger-production.up.railway.app`
4. Visit `https://payleger-production.up.railway.app/docs`

**You should see FastAPI's Swagger UI.** This is your live, interactive API documentation. This URL goes on your resume and GitHub README.

---

## Step 8 — Verify Everything Works End-to-End

Do these in order in your Swagger UI (`/docs`):

1. **Register a user**
   - `POST /auth/register` → `{"email": "test@example.com", "password": "Test1234!", "full_name": "Test User"}`
   - Expected: 201 with user_id

2. **Login and get token**
   - `POST /auth/login` → same credentials
   - Expected: `{"access_token": "eyJ...", "token_type": "bearer"}`
   - Copy the token

3. **Authorize in Swagger**
   - Click the **"Authorize"** button (top right of Swagger UI)
   - Enter: `Bearer eyJ...` (your token)

4. **Check balance**
   - `GET /wallet/balance`
   - Expected: `{"balance": "0.00", "currency": "NGN"}`

5. **Fund your wallet**
   - `POST /wallet/fund` with header `Idempotency-Key: test-key-001`
   - Body: `{"amount": 10000}`
   - Expected: new balance 10000.00

6. **Register a second user** and **fund them too**

7. **Transfer between users**
   - `POST /wallet/transfer` with header `Idempotency-Key: transfer-key-001`
   - Body: `{"recipient_email": "second@example.com", "amount": 2000}`

8. **Test idempotency** — send the exact same transfer request again with the same `Idempotency-Key: transfer-key-001`
   - Expected: same response as before, no second transfer in the ledger

9. **Run reconciliation**
   - `POST /reconciliation/run`
   - Expected: `{"wallets_checked": 2, "discrepancies_found": 0}`

If all 9 pass — your deployment is complete and fully working.

---

## Step 9 — Update Your README

Your GitHub README should now include the live URL. Use this template for the top section:

```markdown
## Live API

Base URL: `https://payleger-production.up.railway.app`
Interactive docs: `https://payleger-production.up.railway.app/docs`

> Deployed on Railway with PostgreSQL and Redis. CI/CD via GitHub Actions.
```

---

## Step 10 — What Gets Charged (Stay Within Free Tier)

Railway's free Starter plan gives you **$5 of usage credits per month**. PayLedger's stack at idle uses roughly:

| Service | ~Monthly cost at idle |
|---|---|
| FastAPI app (512MB RAM) | ~$2.00 |
| PostgreSQL | ~$1.00 |
| Redis | ~$0.50 |
| **Total** | **~$3.50/month** |

You stay within free limits as long as you're not serving real traffic. If credits run low, Railway emails you a warning before shutting anything down.

**To avoid surprises:**
- Set a spend limit in Railway → Settings → Billing → set max to $0 (this keeps you on free tier only)
- Railway will sleep idle services automatically on the free tier

---

## After Deployment — What to Put on Your Resume

Update your PayLedger resume entry to include:

```
Deployed on Railway (PostgreSQL + Redis) — live at payleger-production.up.railway.app/docs
CI/CD pipeline via GitHub Actions with automated test runs on every pull request
```

---

## Troubleshooting Reference

**"My deployment keeps failing with exit code 1"**
→ Read the full build logs. The actual error is almost always 3-4 lines before the final "Deploy failed" message.

**"Migrations ran but tables don't exist"**
→ Check that your `alembic.ini` `sqlalchemy.url` is NOT hardcoded — it must read from env var.

**"I can reach /health but /docs returns 404"**
→ Check that FastAPI is not mounted at a sub-path. `app = FastAPI()` should be at root.

**"Redis connection refused"**
→ Your REDIS_URL is wrong. Redis on Railway uses a specific format — copy it exactly from the Redis service Variables tab, don't type it manually.

**"I pushed a fix but old code is still running"**
→ Railway auto-deploys on push to `main`. Check the Deployments tab — your new deploy might still be building.

---

*End of Railway Deployment Guide — PayLedger*
