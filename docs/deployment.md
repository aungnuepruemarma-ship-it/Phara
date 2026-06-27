# Deployment Guide — Stage 1 Free MVP

Estimated monthly cost: **$0–10** (depends on AI API usage only).

---

## Services

| Service | Platform | What it does |
|---------|----------|--------------|
| Code | GitHub | Source + CI/CD |
| Frontend | Cloudflare Pages | Next.js static export |
| Backend | Render (Free tier) | FastAPI + workers |
| Database | Supabase (Free tier) | PostgreSQL |
| Vector DB | Qdrant Cloud (Free tier) | Embeddings search |
| Cache | Upstash (Free tier) | Redis / session cache |
| File storage | Cloudflare R2 (Free 10 GB) | PDF uploads |

---

## Step 1 — Supabase (Database)

1. Create account at [supabase.com](https://supabase.com)
2. New project → note the **password** you set
3. Go to **Project Settings → Database → Connection string**
4. Copy the **Transaction Mode** pooler URL (port 6543):
   ```
   postgresql+asyncpg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
5. Run migrations once locally against Supabase:
   ```bash
   DATABASE_URL="postgresql+asyncpg://..." alembic upgrade head
   ```

---

## Step 2 — Qdrant Cloud (Vector DB)

1. Create account at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Create a free cluster (1 GB RAM)
3. Go to **API Keys** → create key
4. Note the **cluster URL** (e.g. `xyz.us-east-1.aws.cloud.qdrant.io`) and **API key**

---

## Step 3 — Upstash (Redis Cache)

1. Create account at [console.upstash.com](https://console.upstash.com)
2. Create a Redis database (free tier: 10k requests/day)
3. Go to **Connect → .env** tab
4. Copy the `REDIS_URL` — it starts with `rediss://` (TLS)

---

## Step 4 — Cloudflare R2 (File Storage)

1. Log in to [dash.cloudflare.com](https://dash.cloudflare.com)
2. Go to **R2 → Create bucket** → name it `uil-papers`
3. Go to **R2 → Manage API Tokens** → create token with **Object Read & Write**
4. Note: **Account ID**, **Access Key ID**, **Secret Access Key**
5. Set `USE_R2_STORAGE=true` in Render environment variables

R2 free tier: 10 GB storage, 1M Class A ops/month — plenty for MVP.

---

## Step 5 — Render (Backend)

1. Create account at [render.com](https://render.com)
2. **New → Web Service** → connect GitHub repo
3. Settings:
   - **Root directory**: `backend`
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
   - **Health check path**: `/api/v1/health`
4. Add all environment variables from `.env.example` under **Environment**
5. The `render.yaml` in the repo root pre-fills most of these automatically

> **Note**: Free Render instances sleep after 15 minutes of inactivity and take ~30s to wake.
> This is fine for MVP. Upgrade to Starter ($7/mo) for always-on.

---

## Step 6 — Cloudflare Pages (Frontend)

1. Go to [pages.cloudflare.com](https://pages.cloudflare.com)
2. **Create a project** → connect GitHub repo
3. Settings:
   - **Framework preset**: Next.js (Static HTML Export)
   - **Build command**: `npm run build`
   - **Build output directory**: `out`
   - **Root directory**: `frontend`
4. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = your Render backend URL (e.g. `https://uil-backend.onrender.com/api/v1`)
5. Deploy

Pages free tier: unlimited requests, 500 builds/month — more than enough.

---

## Step 7 — GitHub Secrets

Add these secrets in **GitHub → Settings → Secrets → Actions**:

| Secret | Where to get it |
|--------|----------------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare → API Tokens → Create Token (Cloudflare Pages: Edit) |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare → Right sidebar |
| `NEXT_PUBLIC_API_URL` | Your Render service URL |

---

## CI/CD Flow

```
git push → main
    │
    ├── test-backend.yml  — pytest (SQLite + in-memory Qdrant)
    │
    └── deploy-frontend.yml — npm run build → wrangler pages deploy
```

Render deploys automatically when GitHub pushes to `main` (auto-deploy is on in `render.yaml`).

---

## Local Development (unchanged)

```bash
# Still works exactly as before
docker compose up
```

All stage-1 env vars are optional locally — docker-compose overrides use local services.

---

## Stage 2 Upgrades (when needed)

- Render Starter ($7/mo) — always-on, no cold starts
- Supabase Pro ($25/mo) — daily backups, larger DB
- Qdrant Cloud growth plan — larger vector storage
- Upstash Pro — higher request limits
