# AirSense Pakistan Model Governance & Promotion Policy

## 1. Overview
AirSense Pakistan enforces controlled, audited model promotion and rollback procedures.

Automatic promotion of unreviewed models is strictly forbidden.

---

## 2. Promotion Lifecycle & States

```
[ Training ] ---> [ Succeeded ] ---> Nominate ---> [ Candidate ] ---> Authorised Promote ---> [ Production ]
                        |                                                                            |
                        +---> Fail / Insufficient                                                    v
                                                                                                Rollback
```

1. **Candidate Eligibility**: A model run must achieve `training_status: "succeeded"`, pass SHA-256 artifact reload tests, and complete walk-forward validation.
2. **Authorised Promotion**: An administrator explicitly approves promotion (`POST /api/v1/models/{run_id}/promote`). The system demotes any prior production model for the exact same campus, station, and horizon transactionally.
3. **Rollback**: If a production model degrades, administrators can trigger an explicit rollback (`POST /api/v1/models/{run_id}/rollback`).
