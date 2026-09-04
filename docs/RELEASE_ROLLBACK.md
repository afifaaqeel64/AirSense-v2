# AirSense Pakistan Release Rollback Procedure

> Scope: Emergency Application & Model Rollback Operations

## 1. Application Software Rollback

### Containerized Rollback (Docker)
To revert to a prior container image release:
```bash
docker-compose down
git checkout v0.9.0  # Or target stable release tag
docker-compose up -d --build
```

### Database Migration Rollback (Alembic)
To roll back the database schema by 1 revision:
```bash
alembic downgrade -1
```

---

## 2. Machine Learning Model Rollback

If a newly promoted model exhibits unexpected forecast errors:
1. Open the **Model Lab** tab in the Operational Control Centre.
2. Locate the prior production model run ID (e.g. `run_baseline_01`).
3. Execute a model rollback via API:
```bash
curl -X POST "http://localhost:8000/api/v1/models/run_current_123/rollback" \
     -H "X-Admin-Token: your_admin_token" \
     -H "Content-Type: application/json" \
     -d '{"rollback_to_run_id": "run_prior_456", "reason": "Emergency performance rollback"}'
```
4. Verify that the previous model is restored as `is_production = True`.
