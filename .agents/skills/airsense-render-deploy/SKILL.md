---
name: airsense-render-deploy
description: >-
  Step-by-step automated workflow and checklist for deploying AirSense Pakistan
  backend API, PostgreSQL database, and 24/7 background scheduler to Render Cloud Infrastructure.
---

# AirSense Pakistan: Render Cloud Deployment Skill

This skill documents and executes the automated cloud deployment of the AirSense Pakistan backend using Render's Infrastructure-as-Code (render.yaml) Blueprint.

## 1. Prerequisites & Assets Checklist
- render.yaml: Configured with services (airsense-api) and databases (airsense-db).
- requirements.txt: Includes fastapi, uvicorn, psycopg2-binary, asyncpg, sqlalchemy, and aiosqlite.
- apps/api/db/session.py: Normalizes postgres:// URLs to postgresql+asyncpg:// automatically.
- apps/api/main.py: Runs database table migration and seed insertion inside lifespan automatically.

## 2. 1-Click Render Deployment Procedure
1. Connect GitHub Repository to dashboard.render.com.
2. Launch Blueprint: Click New + -> Blueprint -> select AirSense-v2 repo.
3. Click Apply: Render provisions web service, PostgreSQL database, and launches API at https://airsense-api.onrender.com.

## 3. Post-Deployment Verification
Verify liveness and readiness probes:
- GET https://airsense-api.onrender.com/api/v1/health/liveness
- GET https://airsense-api.onrender.com/api/v1/health/readiness
- GET https://airsense-api.onrender.com/api/v1/ingest/sensors/diagnostic
