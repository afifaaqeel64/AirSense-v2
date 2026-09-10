# AirSense Pakistan Deployment Guide

This guide covers deployment procedures for AirSense Pakistan across supported execution modes.

## 1. Mode A: Local Python & SQLite Execution (Zero-Cost Baseline)

Mode A runs directly on standard laptop or desktop hardware using Python and SQLite.

### Requirements
- Python 3.12+
- `pip` package manager

### Step-by-Step Instructions

1. **Configure Environment**:
   ```bash
   cp .env.example .env
   ```

2. **Install Python Dependencies**:
   ```bash
   py -m pip install -r requirements.txt
   ```

3. **Run Application**:
   ```bash
   py -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
   ```

4. **Verify Health Endpoints**:
   ```bash
   curl http://127.0.0.1:8000/api/v1/health
   curl http://127.0.0.1:8000/api/v1/ready
   ```

---

## 2. Mode B: Campus Local Server (Docker Compose + PostgreSQL)

Mode B provides robust campus-level execution using Docker Compose.

### Requirements
- Docker Engine & Docker Compose

### Step-by-Step Instructions

1. **Configure Production Environment**:
   ```bash
   cp .env.example .env
   # Edit .env to supply DB_PASSWORD and SECRET values
   ```

2. **Launch Docker Stack**:
   ```bash
   docker-compose up -d --build
   ```

3. **Check Container Status**:
   ```bash
   docker-compose ps
   ```

4. **View Application Logs**:
   ```bash
   docker-compose logs -f api
   ```

---

## 3. Mode C: Cloud Managed PostgreSQL (Supabase) & Vercel / Render

Mode C connects AirSense to a 24/7 managed cloud PostgreSQL instance (e.g., Supabase) with zero server maintenance.

### 1. Database URL Configuration
In your `.env` (or cloud dashboard environment variables):
```bash
# Supabase PostgreSQL Connection String
DATABASE_URL=postgresql://postgres:7EZgyMcqYi%269qUE@db.vppczkvawiaptiygrqhx.supabase.co:5432/postgres
```
*Note: Characters like `&` in passwords must be URL-encoded as `%26`. The backend automatically converts `postgresql://` to `postgresql+asyncpg://` and detects IPv4/IPv6 reachability to route through the regional connection pooler (`aws-0-ap-northeast-2.pooler.supabase.com:5432`) when running on IPv4-only networks or serverless platforms.*

### 2. Schema Initialization & Seeding
To initialize all 17 public schema tables and seed the pilot stations (`BIC-KHI-ROOF-01`, `AIRSENSE-NODE-KHI-01`):
```bash
py scripts/init_and_seed_supabase.py
```

### 3. Vercel Serverless Deployment
Add the `DATABASE_URL` in your Vercel Project Dashboard:
1. Navigate to **Project Settings > Environment Variables**.
2. Add Key: `DATABASE_URL`, Value: `postgresql://postgres:7EZgyMcqYi%269qUE@db.vppczkvawiaptiygrqhx.supabase.co:5432/postgres`.
3. Select Environments: **Production**, **Preview**, **Development**.
4. Save and trigger a new deployment.

---

## 4. Rollback Procedure

- If a deployment fails, revert to previous stable codebase branch or container tag.
- SQLite database backups are maintained as `.db.bak` copies prior to migrations.
