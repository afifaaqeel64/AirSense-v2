# AirSense Pakistan Backup & Restore Procedures

This document provides procedures for database backup, point-in-time recovery, and restore verification across SQLite (Mode A) and PostgreSQL (Mode B) deployments.

## 1. Mode A: SQLite Backup & Restore (Local Laptop)

### Backup Command
```bash
py scripts/backup.py
```
Outputs timestamped copy to `./data/backups/airsense_backup_YYYYMMDD_HHMMSS.db`.

### Restore Command
```bash
py scripts/restore.py airsense_backup_20260727_120000.db
```

## 2. Mode B: PostgreSQL / TimescaleDB Backup & Restore (Campus Server)

### Backup Command
```bash
docker exec -t airsense-db pg_dump -U airsense -d airsense -F c -b -v -f /var/lib/postgresql/data/airsense_pg_backup.dump
```

### Restore Command
```bash
docker exec -i airsense-db pg_restore -U airsense -d airsense -v /var/lib/postgresql/data/airsense_pg_backup.dump
```
