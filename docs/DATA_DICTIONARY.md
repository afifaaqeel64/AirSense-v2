# AirSense Pakistan Data Dictionary

This document defines canonical field names, data types, units, constraints, and descriptions for all core entities in AirSense Pakistan.

## 1. Entity Definitions

### 1.1 Campus (`campuses`)
| Field Name | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | String(36) | Primary Key | UUID primary identifier. |
| `code` | String(50) | Unique, Index | Unique campus code (`ISB_CAMPUS`, `KHI_CAMPUS`). |
| `name` | String(100) | Not Null | Human-readable campus name. |
| `city` | String(50) | Not Null | City location (`Islamabad`, `Karachi`). |
| `contact_name` | String(100) | Not Null | Primary contact (`Muhammad M. Qureshi` for ISB, `Areesha` for KHI). |
| `latitude` | Float | Nullable | Campus rooftop latitude (-90.0 to 90.0). |
| `longitude` | Float | Nullable | Campus rooftop longitude (-180.0 to 180.0). |
| `status` | String(50) | Default: `configuration_required` | Operational status (`active`, `configuration_required`). |
| `created_at` | DateTime(UTC) | Not Null | UTC creation timestamp. |

### 1.2 Station (`stations`)
| Field Name | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | String(36) | Primary Key | UUID primary identifier. |
| `campus_id` | String(36) | FK -> `campuses.id` | Associated campus. |
| `name` | String(100) | Not Null | Station name. |
| `station_type` | String(50) | Not Null | Type (`onsite_esp32`, `external_provider`). |
| `is_active` | Boolean | Default: True | Active status flag. |
| `created_at` | DateTime(UTC) | Not Null | UTC creation timestamp. |

### 1.3 Device (`devices`)
| Field Name | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | String(36) | Primary Key | UUID primary identifier. |
| `station_id` | String(36) | FK -> `stations.id` | Associated station. |
| `mac_address` | String(50) | Unique, Index | Physical MAC address of ESP32 board. |
| `device_token_hash` | String(128) | Not Null | SHA-256 hash of device authentication token. |
| `firmware_version` | String(50) | Default: `1.0.0` | ESP32 firmware build version. |
| `is_active` | Boolean | Default: True | Device active status. |

### 1.4 RawReading (`raw_readings`)
| Field Name | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | String(36) | Primary Key | UUID primary identifier. |
| `timestamp` | DateTime(UTC) | Index, Not Null | Measurement time in UTC. |
| `campus_code` | String(50) | Index, Not Null | Target campus code. |
| `ingest_source` | String(50) | Not Null | Ingestion source (`esp32_http`, `csv_upload`). |
| `raw_payload` | Text | Not Null | JSON payload string as received. |

### 1.5 Observation (`observations`)
| Field Name | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | String(36) | Primary Key | UUID primary identifier. |
| `timestamp` | DateTime(UTC) | Index, Not Null | Measurement time in UTC. |
| `campus_code` | String(50) | Index, Not Null | Associated campus code. |
| `pm25` | Float | 0.0 to 1000.0 ug/m3 | Validated PM2.5 concentration. |
| `pm10` | Float | 0.0 to 1000.0 ug/m3 | Validated PM10 concentration. |
| `temperature` | Float | -20.0 to 60.0 C | Ambient temperature in Celsius. |
| `humidity` | Float | 0.0 to 100.0 % | Relative humidity percentage. |
| `qc_status` | String(50) | Default: `pass` | QC result (`pass`, `flagged_spike`, `stuck_sensor`). |

## 2. Standard Units

- PM2.5 Concentration: micrograms per cubic metre ($\mu g/m^3$)
- PM10 Concentration: micrograms per cubic metre ($\mu g/m^3$)
- Temperature: degrees Celsius ($^\circ C$)
- Relative Humidity: percent ($\%$)
- Timestamps: ISO 8601 UTC string (e.g. `2026-07-27T12:00:00Z`)
