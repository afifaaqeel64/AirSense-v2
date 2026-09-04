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

## 3. Rollback Procedure

- If a deployment fails, revert to previous stable codebase branch or container tag.
- SQLite database backups are maintained as `.db.bak` copies prior to migrations.
