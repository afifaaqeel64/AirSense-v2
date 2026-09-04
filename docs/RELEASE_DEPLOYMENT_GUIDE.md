# AirSense Pakistan Release & Deployment Guide

> Target Stage: Campus Pilot Phase 1 Software Release Candidate  
> Pilot Deployment Locations: Islamabad & Karachi Campuses

## Overview
This guide provides step-by-step instructions for packaging, configuring, deploying, and operating **AirSense Pakistan** in production or pilot environments.

---

## 1. System Requirements

### Hardware Requirements
- **Server / Local Workstation**: Dual-Core CPU, 4 GB RAM, 20 GB Disk Space.
- **Network**: Local Area Network (LAN) or Internet connection for external provider syncs.

### Software Prerequisites
- Python 3.12+ (for local native deployment)
- Docker 24.0+ and Docker Compose v2.20+ (for containerized deployment)

---

## 2. Option A: Containerized Docker Deployment (Recommended)

### Step 1: Environment Configuration
Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```
Update production settings in `.env`:
```env
AIR_SENSE_ENV=production
AIR_SENSE_TIMEZONE=Asia/Karachi
ADMIN_API_TOKEN=your_secure_admin_token_2026
DEVICE_TOKEN_SALT=your_secure_device_salt_2026
ISLAMABAD_CONTACT_NAME=Muhammad M. Qureshi
KARACHI_CONTACT_NAME=Areesha
```

### Step 2: Build & Start Services
```bash
docker-compose up -d --build
```

### Step 3: Verify Service Health
Check container logs and health endpoints:
```bash
docker-compose ps
curl -f http://localhost:8000/api/v1/health
curl -f http://localhost:8000/api/v1/ready
```

Access the **Operational Control Centre** dashboard at:
`http://localhost:8000/ops`

---

## 3. Option B: Native Local Python Deployment

### Step 1: Virtual Environment Setup
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Run Database Migrations
```bash
alembic upgrade head
```

### Step 3: Launch FastAPI Application
```bash
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

---

## 4. Operational Backup & Verification

To create an operational backup:
```bash
python scripts/backup_restore.py
```
Or via HTTP API:
```bash
curl -X POST "http://localhost:8000/api/v1/admin/backups" \
     -H "X-Admin-Token: your_secure_admin_token_2026" \
     -H "Content-Type: application/json" \
     -d '{"description": "Pre-deployment backup"}'
```
