# AirSense Pakistan Operations Runbook

This runbook provides step-by-step procedures for routine operational monitoring, troubleshooting, data export, and system recovery.

## 1. Routine System Verification

Run health and readiness checks:
```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/ready
curl http://localhost:8000/api/v1/version
```

Expected readiness output:
- `status`: `ready`
- `database`: `connected`
- `pilots.islamabad.contact`: `Muhammad M. Qureshi`
- `pilots.karachi.contact`: `Areesha`

## 2. Handling Missing Coordinates

If campus status reports `configuration_required`:
1. Obtain verified GPS rooftop coordinates for the campus.
2. Update `.env` with `ISLAMABAD_LATITUDE`, `ISLAMABAD_LONGITUDE`, `KARACHI_LATITUDE`, `KARACHI_LONGITUDE`.
3. Restart backend service.

## 3. Database Maintenance & Backup (Mode A)

To backup local SQLite database:
```bash
cp data/airsense.db data/backups/airsense_backup_$(date +%Y%m%d).db
```

## 4. Secret Exposure Incident Protocol

If a key or secret is accidentally exposed:
1. Immediately revoke the key in the provider portal (or regenerate `ADMIN_API_TOKEN` / `DEVICE_TOKEN_SALT`).
2. Update `.env` file on local server.
3. Restart backend application.
4. Verify Git history contains no committed `.env` files.
