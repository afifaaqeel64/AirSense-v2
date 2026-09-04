# AirSense Pakistan Database Schema Documentation

## 1. Overview and Architecture

AirSense Pakistan implements a multi-campus, multi-station, multi-device time-series database design supporting:
- **Mode A**: SQLite (`./data/airsense.db`) via `aiosqlite` for zero-cost local laptop execution.
- **Mode B**: PostgreSQL / TimescaleDB via `asyncpg` for campus server deployment.

All timestamps are explicitly stored in **UTC** with timezone awareness (`DateTime(timezone=True)`).

---

## 2. Entity Relationship Diagram

```
Campuses (1) ---< (N) Stations (1) ---< (N) Devices
   |                      |
   | (1)                  | (1)
   v                      v
ImportBatches (1) -< (N) RawReadings (1) -< (1) QualityAssessments
                          |
                          v
                    Observations (1) -> (1) HourlyObservations
```

---

## 3. Detailed Entity Schema Definitions

### 3.1 `campuses`
- **Primary Key**: `id` (UUID String)
- **Unique Constraint**: `code` (`ISB_CAMPUS`, `KHI_CAMPUS`)
- **Key Columns**: `name`, `city`, `country`, `latitude`, `longitude`, `timezone`, `status`, `location_status`, `contact_name`
- **Location Status**: Defaults to `unverified` if latitude/longitude are NULL (`configuration_required`).

### 3.2 `stations`
- **Primary Key**: `id` (UUID String)
- **Foreign Key**: `campus_id` -> `campuses.id` (RESTRICT deletion)
- **Unique Constraint**: `station_code`
- **Key Columns**: `station_name`, `installation_location`, `latitude`, `longitude`, `elevation_m`, `installation_date`, `status`, `sampling_interval_seconds`, `firmware_version`, `last_seen_at`, `monitoring_started_at`

### 3.3 `devices`
- **Primary Key**: `id` (UUID String)
- **Foreign Key**: `station_id` -> `stations.id` (RESTRICT deletion)
- **Unique Constraint**: `device_uid`
- **Security**: `token_hash` stores SHA-256 hash of device authentication token (never plain text!).
- **Key Columns**: `device_type`, `model`, `serial_number`, `token_last_rotated_at`, `firmware_version`, `status`, `last_authenticated_at`

### 3.4 `maintenance_events`
- **Primary Key**: `id` (UUID String)
- **Foreign Keys**: `campus_id`, `station_id`, `device_id`
- **Key Columns**: `started_at`, `ended_at`, `event_type`, `description`, `performed_by`
- **Rules**: Excludes periods from uptime calculations and prevents interpolation through maintenance.

### 3.5 `import_batches`
- **Primary Key**: `id` (UUID String)
- **Foreign Keys**: `campus_id`, `station_id`
- **Key Columns**: `filename`, `original_filename`, `file_hash` (SHA-256), `file_size_bytes`, `uploaded_at`, `detected_encoding`, `delimiter`, `timezone_assumption`, `mapping_json`, `conversions_json`, `rows_received`, `rows_valid`, `rows_rejected`, `rows_duplicate`, `rows_committed`, `status` (`preview_ready`, `committed`, `failed`, `rejected`)

### 3.6 `raw_readings`
- **Primary Key**: `id` (UUID String)
- **Foreign Keys**: `campus_id`, `station_id`, `device_id`, `import_batch_id`
- **Deduplication Key**: Composite index on (`station_id`, `observed_at`, `sequence_number`) and `content_hash`
- **Key Columns**: `observed_at`, `source_timestamp_original`, `received_at`, `source`, `pm1`, `pm2_5`, `pm10`, `temperature_c`, `humidity_pct`, `pressure_hpa`, `rain_flag`, `wind_speed_m_s`, `wind_direction_deg`, `aqi`, `payload_json`, `idempotency_key`, `sequence_number`, `content_hash`
- **Rule**: Raw values are preserved exactly. Impossible values are NEVER overwritten in `raw_readings`.

### 3.7 `quality_assessments`
- **Primary Key**: `id` (UUID String)
- **Foreign Key**: `raw_reading_id` -> `raw_readings.id` (CASCADE deletion)
- **Key Columns**: `quality_score` (0.0 to 1.0), `quality_status` (`accepted`, `accepted_with_warning`, `review_required`, `rejected`, `duplicate`, `stale`), flags (`impossible_value_flag`, `high_humidity_flag`, `gap_flag`, `duplicate_flag`, `stale_flag`, `spike_review_flag`, `ordering_consistency_flag`, `timestamp_flag`), `interpolated_fields_json`, `validation_messages_json`, `qc_version`

### 3.8 `observations`
- **Primary Key**: `id` (UUID String)
- **Foreign Keys**: `raw_reading_id`, `campus_id`, `station_id`
- **Unique Constraint**: (`station_id`, `source`, `observed_at`)
- **Key Columns**: `observed_at`, `source`, `source_type` (`ground_truth`, `external_model`), pollutants (`pm1`, `pm2_5`, `pm10`), weather (`temperature_c`, `humidity_pct`, `pressure_hpa`, `rain_flag`, `wind_speed_m_s`, `wind_direction_deg`), `quality_score`, `is_interpolated`, `is_model_eligible`, `eligibility_reason`, `lineage_json`

### 3.9 `hourly_observations`
- **Primary Key**: `id` (UUID String)
- **Foreign Keys**: `campus_id`, `station_id`
- **Unique Constraint**: (`station_id`, `source`, `hour_start`)
- **Key Columns**: `hour_start`, `pm1_mean`, `pm2_5_mean`, `pm2_5_median`, `pm10_mean`, `pm10_median`, `temperature_mean`, `humidity_mean`, `pressure_mean`, `rain_detected`, `rain_fraction`, `wind_speed_mean`, `wind_direction_circular_mean`, `contributing_count`, `expected_count`, `completeness_pct`, `average_quality_score`, `high_humidity_fraction`, `has_interpolation`, `is_model_eligible`

### 3.10 `external_provider_runs`
- **Primary Key**: `id` (UUID String)
- **Foreign Key**: `campus_id`
- **Key Columns**: `provider` (`open_meteo_weather`, `open_meteo_air_quality`), `started_at`, `completed_at`, `status` (`success`, `failed`, `rate_limited`, `skipped_no_coords`), `records_received`, `records_inserted`, `sanitized_error_message`, `retry_count`

---

## 4. SQLite vs. PostgreSQL & TimescaleDB Migration Notes

1. **SQLite Execution (Mode A)**: Handled via `aiosqlite`. JSON fields are stored as text-serialized JSON strings. Unique constraints and foreign key enforcement are active.
2. **PostgreSQL Execution (Mode B)**: Native JSONB type supported for `payload_json`, `validation_report_json`, and `lineage_json`.
3. **TimescaleDB Mapping**: The `raw_readings` and `observations` tables map directly to TimescaleDB hypertables partitioned by `observed_at` with 7-day chunk intervals.
