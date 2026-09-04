# AirSense Pakistan Phase 6 Security Review & Audit

> Stage: Campus Pilot Phase 1 Software Release Candidate  
> Security Posture: Production Hardened & Zero-Cost Compliant

## Executive Summary
This document provides a comprehensive security review of the **AirSense Pakistan** platform. All Phase 6 security controls have been audited to ensure defense-in-depth across API authentication, token storage, data ingestion, artifact loading, error handling, and administrative safety.

---

## 1. Authentication & Access Control

### 1.1 Ingestion Device Authentication (`X-Device-Token`)
- ESP32 sensor stations authenticate via `Authorization: Bearer <token>` or `X-Device-Token: <token>`.
- Plaintext device tokens are generated using cryptographically secure randomness (`secrets.token_hex(24)`).
- Tokens are hashed using SHA-256 with a server-side secret salt (`DEVICE_TOKEN_SALT`).
- **Token Redaction**: Raw `token_hash` values are strictly excluded from all database responses and API models.
- **One-Time Display**: Raw plaintext tokens are returned exactly once upon initial device creation or rotation.

### 1.2 Administrative Route Protection (`X-Admin-Token`)
- Sensitive administrative routes (campus creation, station creation, device token rotation, model promotion/rollback, system backups) require `X-Admin-Token` header.
- Token comparison uses constant-time string comparison (`secrets.compare_digest`) to prevent timing side-channel attacks.

---

## 2. Input Validation & Safe Execution

### 2.1 Safe Code Lab Sandbox
- Interactive inference (`POST /api/v1/inference/run`) accepts strictly structured JSON feature vectors.
- Arbitrary Python code, shell commands, raw SQL, path navigation, and dynamic module loading are strictly disabled.

### 2.2 Model Artifact Deserialization
- Model binaries (`model.joblib`, `residuals.npz`) are loaded strictly from verified local artifact paths within `data/models/`.
- Every model run directory contains a `checksums.json` manifest recording SHA-256 hashes for `model.joblib`, `residuals.npz`, `feature_contract.json`, and `metrics.json`.

---

## 3. Data Safety & Error Redaction

### 3.1 Error Handling & Log Security
- Unhandled exceptions return generic, sanitized JSON error responses without exposing internal stack traces, private file system paths, database connection strings, or server secrets.
- Production logging suppresses secret environment variables and token values.

### 3.2 SQL & File Injection Defense
- All database queries use SQLAlchemy parameter binding or async ORM statements.
- CSV imports validate column names, timestamp formats, and numeric bounds prior to database commit.

---

## 4. Summary of Security Verification Gates

| Security Requirement | Implementation | Status |
| :--- | :--- | :--- |
| **CORS Isolation** | Restricts allowed origins via `CORS_ORIGINS` config | ✅ Passed |
| **Token Hashing** | SHA-256 salted hashing for ESP32 tokens | ✅ Passed |
| **Secret Redaction** | No token hashes or keys exposed in API JSON | ✅ Passed |
| **Safe Error Handling** | Stack traces & paths stripped from 400/500 errors | ✅ Passed |
| **Non-Root Container** | Container user `airsense` (UID 1000) | ✅ Passed |
| **Backup Integrity** | ZIP archive SHA-256 verification | ✅ Passed |
