"""AirSense Pakistan Phase 5 SQLAlchemy Domain Models."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    String, Float, DateTime, Boolean, ForeignKey, Integer, Text, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from apps.api.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Campus(Base):
    __tablename__ = "campuses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(50), nullable=False)
    country: Mapped[str] = mapped_column(String(50), default="Pakistan", nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Karachi", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="configuration_required", nullable=False)
    location_status: Mapped[str] = mapped_column(String(50), default="unverified", nullable=False)
    contact_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    stations: Mapped[list["Station"]] = relationship("Station", back_populates="campus", cascade="all, delete-orphan")
    maintenance_events: Mapped[list["MaintenanceEvent"]] = relationship("MaintenanceEvent", back_populates="campus")


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campus_id: Mapped[str] = mapped_column(String(36), ForeignKey("campuses.id", ondelete="RESTRICT"), nullable=False, index=True)
    station_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    station_name: Mapped[str] = mapped_column(String(100), nullable=False)
    installation_location: Mapped[str] = mapped_column(String(200), default="Main Building Rooftop", nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    elevation_m: Mapped[float] = mapped_column(Float, nullable=True)
    installation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    sampling_interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    firmware_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    monitoring_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    campus: Mapped["Campus"] = relationship("Campus", back_populates="stations")
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="station", cascade="all, delete-orphan")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    station_id: Mapped[str] = mapped_column(String(36), ForeignKey("stations.id", ondelete="RESTRICT"), nullable=False, index=True)
    device_uid: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), default="ESP32_WROOM_32D", nullable=False)
    model: Mapped[str] = mapped_column(String(100), default="AirSense Station V1", nullable=False)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    token_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    token_last_rotated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    calibration_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    calibration_notes: Mapped[str] = mapped_column(Text, nullable=True)
    firmware_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    last_authenticated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    station: Mapped["Station"] = relationship("Station", back_populates="devices")


class MaintenanceEvent(Base):
    __tablename__ = "maintenance_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campus_id: Mapped[str] = mapped_column(String(36), ForeignKey("campuses.id", ondelete="CASCADE"), nullable=False, index=True)
    station_id: Mapped[str] = mapped_column(String(36), ForeignKey("stations.id", ondelete="CASCADE"), nullable=True, index=True)
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(50), default="servicing", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    performed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    campus: Mapped["Campus"] = relationship("Campus", back_populates="maintenance_events")


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campus_id: Mapped[str] = mapped_column(String(36), ForeignKey("campuses.id", ondelete="RESTRICT"), nullable=False, index=True)
    station_id: Mapped[str] = mapped_column(String(36), ForeignKey("stations.id", ondelete="RESTRICT"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(100), default="operator", nullable=False)
    detected_encoding: Mapped[str] = mapped_column(String(20), default="utf-8", nullable=False)
    delimiter: Mapped[str] = mapped_column(String(5), default=",", nullable=False)
    timezone_assumption: Mapped[str] = mapped_column(String(50), default="Asia/Karachi", nullable=False)
    mapping_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    conversions_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    rows_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_valid: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_duplicate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_committed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    validation_report_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="preview_ready", nullable=False)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class RawReading(Base):
    __tablename__ = "raw_readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campus_id: Mapped[str] = mapped_column(String(36), ForeignKey("campuses.id", ondelete="RESTRICT"), nullable=False, index=True)
    station_id: Mapped[str] = mapped_column(String(36), ForeignKey("stations.id", ondelete="RESTRICT"), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id", ondelete="RESTRICT"), nullable=True, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    source_timestamp_original: Mapped[str] = mapped_column(String(100), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="onsite_esp32", nullable=False, index=True)
    pm1: Mapped[float] = mapped_column(Float, nullable=True)
    pm2_5: Mapped[float] = mapped_column(Float, nullable=True)
    pm10: Mapped[float] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float] = mapped_column(Float, nullable=True)
    pressure_hpa: Mapped[float] = mapped_column(Float, nullable=True)
    rain_flag: Mapped[bool] = mapped_column(Boolean, nullable=True)
    wind_speed_m_s: Mapped[float] = mapped_column(Float, nullable=True)
    wind_direction_deg: Mapped[float] = mapped_column(Float, nullable=True)
    aqi: Mapped[int] = mapped_column(Integer, nullable=True)
    aqi_standard: Mapped[str] = mapped_column(String(50), default="US_EPA", nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    pollutant_metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    ingested_via: Mapped[str] = mapped_column(String(50), default="esp32_http", nullable=False)
    import_batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_raw_dedup_onsite", "station_id", "observed_at", "sequence_number", unique=False),
    )


class QualityAssessment(Base):
    __tablename__ = "quality_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    raw_reading_id: Mapped[str] = mapped_column(String(36), ForeignKey("raw_readings.id", ondelete="CASCADE"), nullable=False, index=True)
    quality_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    quality_status: Mapped[str] = mapped_column(String(50), default="accepted", nullable=False, index=True)
    impossible_value_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    high_humidity_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gap_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stale_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    spike_review_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ordering_consistency_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timestamp_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    interpolated_fields_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    validation_messages_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    qc_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    raw_reading_id: Mapped[str] = mapped_column(String(36), ForeignKey("raw_readings.id", ondelete="SET NULL"), nullable=True, index=True)
    campus_id: Mapped[str] = mapped_column(String(36), ForeignKey("campuses.id", ondelete="RESTRICT"), nullable=False, index=True)
    station_id: Mapped[str] = mapped_column(String(36), ForeignKey("stations.id", ondelete="RESTRICT"), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="onsite_esp32", nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), default="ground_truth", nullable=False)
    pm1: Mapped[float] = mapped_column(Float, nullable=True)
    pm2_5: Mapped[float] = mapped_column(Float, nullable=True)
    pm10: Mapped[float] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float] = mapped_column(Float, nullable=True)
    pressure_hpa: Mapped[float] = mapped_column(Float, nullable=True)
    rain_flag: Mapped[bool] = mapped_column(Boolean, nullable=True)
    wind_speed_m_s: Mapped[float] = mapped_column(Float, nullable=True)
    wind_direction_deg: Mapped[float] = mapped_column(Float, nullable=True)
    aqi: Mapped[int] = mapped_column(Integer, nullable=True)
    aqi_standard: Mapped[str] = mapped_column(String(50), default="US_EPA", nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_interpolated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_model_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    eligibility_reason: Mapped[str] = mapped_column(String(100), default="valid_ground_truth", nullable=False)
    normalization_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    lineage_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("station_id", "source", "observed_at", name="uq_obs_station_source_time"),
    )


class HourlyObservation(Base):
    __tablename__ = "hourly_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campus_id: Mapped[str] = mapped_column(String(36), ForeignKey("campuses.id", ondelete="RESTRICT"), nullable=False, index=True)
    station_id: Mapped[str] = mapped_column(String(36), ForeignKey("stations.id", ondelete="RESTRICT"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), default="onsite_esp32", nullable=False, index=True)
    hour_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    pm1_mean: Mapped[float] = mapped_column(Float, nullable=True)
    pm2_5_mean: Mapped[float] = mapped_column(Float, nullable=True)
    pm2_5_median: Mapped[float] = mapped_column(Float, nullable=True)
    pm10_mean: Mapped[float] = mapped_column(Float, nullable=True)
    pm10_median: Mapped[float] = mapped_column(Float, nullable=True)
    temperature_mean: Mapped[float] = mapped_column(Float, nullable=True)
    humidity_mean: Mapped[float] = mapped_column(Float, nullable=True)
    pressure_mean: Mapped[float] = mapped_column(Float, nullable=True)
    rain_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rain_fraction: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    wind_speed_mean: Mapped[float] = mapped_column(Float, nullable=True)
    wind_direction_circular_mean: Mapped[float] = mapped_column(Float, nullable=True)
    contributing_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expected_count: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    completeness_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    average_quality_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    high_humidity_fraction: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    has_interpolation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_model_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    eligibility_reason: Mapped[str] = mapped_column(String(100), default="sufficient_completeness", nullable=False)
    aggregation_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("station_id", "source", "hour_start", name="uq_hourly_station_source_hour"),
    )


class ExternalProviderRun(Base):
    __tablename__ = "external_provider_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    campus_id: Mapped[str] = mapped_column(String(36), ForeignKey("campuses.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False, index=True)
    http_status: Mapped[int] = mapped_column(Integer, nullable=True)
    request_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    records_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_duplicate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_type: Mapped[str] = mapped_column(String(50), nullable=True)
    sanitized_error_message: Mapped[str] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    response_cache_key: Mapped[str] = mapped_column(String(128), nullable=True)
    rate_limit_limit: Mapped[int] = mapped_column(Integer, nullable=True)
    rate_limit_remaining: Mapped[int] = mapped_column(Integer, nullable=True)
    rate_limit_reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


# --- PHASE 5 DOMAIN ENTITIES ---

class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    campus_id: Mapped[str] = mapped_column(String(36), ForeignKey("campuses.id", ondelete="RESTRICT"), nullable=True, index=True)
    station_id: Mapped[str] = mapped_column(String(36), ForeignKey("stations.id", ondelete="RESTRICT"), nullable=True, index=True)
    run_scope: Mapped[str] = mapped_column(String(50), default="campus", nullable=False)  # campus_station, campus, pooled_campuses, historical_benchmark, development_test
    participating_campuses_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_family: Mapped[str] = mapped_column(String(50), nullable=False)  # persistence, slr, mlr, decision_tree, random_forest, xgboost, lightgbm
    forecast_horizon_hours: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True)
    feature_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    target_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    qc_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    normalization_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    aggregation_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    dataset_fingerprint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    code_version: Mapped[str] = mapped_column(String(50), default="0.1.0-phase5", nullable=False)
    random_seed: Mapped[int] = mapped_column(Integer, default=42, nullable=False)
    training_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    training_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    validation_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    validation_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    training_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    validation_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    validation_folds: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    rmse: Mapped[float] = mapped_column(Float, nullable=True)
    mae: Mapped[float] = mapped_column(Float, nullable=True)
    median_absolute_error: Mapped[float] = mapped_column(Float, nullable=True)
    r2: Mapped[float] = mapped_column(Float, nullable=True)
    mape: Mapped[float] = mapped_column(Float, nullable=True)
    exceedance_precision: Mapped[float] = mapped_column(Float, nullable=True)
    exceedance_recall: Mapped[float] = mapped_column(Float, nullable=True)
    exceedance_f1: Mapped[float] = mapped_column(Float, nullable=True)
    interval_coverage: Mapped[float] = mapped_column(Float, nullable=True)
    interval_mean_width: Mapped[float] = mapped_column(Float, nullable=True)
    persistence_mae: Mapped[float] = mapped_column(Float, nullable=True)
    historical_benchmark_mae: Mapped[float] = mapped_column(Float, nullable=True)
    historical_benchmark_r2: Mapped[float] = mapped_column(Float, nullable=True)
    hyperparameters_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    feature_names_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    package_versions_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(255), nullable=True)
    artifact_checksum: Mapped[str] = mapped_column(String(64), nullable=True)
    preprocessing_artifact_path: Mapped[str] = mapped_column(String(255), nullable=True)
    preprocessing_checksum: Mapped[str] = mapped_column(String(64), nullable=True)
    residual_artifact_path: Mapped[str] = mapped_column(String(255), nullable=True)
    residual_checksum: Mapped[str] = mapped_column(String(64), nullable=True)
    explanation_artifact_path: Mapped[str] = mapped_column(String(255), nullable=True)
    explanation_checksum: Mapped[str] = mapped_column(String(64), nullable=True)
    training_status: Mapped[str] = mapped_column(String(50), default="succeeded", nullable=False, index=True)
    is_candidate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_production: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    promoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    promoted_by: Mapped[str] = mapped_column(String(100), nullable=True)
    promotion_reason: Mapped[str] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str] = mapped_column(Text, nullable=True)
    failure_code: Mapped[str] = mapped_column(String(50), nullable=True)
    sanitized_failure_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class ModelValidationFold(Base):
    __tablename__ = "model_validation_folds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("model_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    fold_number: Mapped[int] = mapped_column(Integer, nullable=False)
    train_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    train_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validation_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validation_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    training_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    rmse: Mapped[float] = mapped_column(Float, nullable=True)
    mae: Mapped[float] = mapped_column(Float, nullable=True)
    median_absolute_error: Mapped[float] = mapped_column(Float, nullable=True)
    r2: Mapped[float] = mapped_column(Float, nullable=True)
    mape: Mapped[float] = mapped_column(Float, nullable=True)
    exceedance_precision: Mapped[float] = mapped_column(Float, nullable=True)
    exceedance_recall: Mapped[float] = mapped_column(Float, nullable=True)
    exceedance_f1: Mapped[float] = mapped_column(Float, nullable=True)
    interval_coverage: Mapped[float] = mapped_column(Float, nullable=True)
    interval_mean_width: Mapped[float] = mapped_column(Float, nullable=True)
    residual_summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("model_run_id", "fold_number", name="uq_fold_run_num"),
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("model_runs.id", ondelete="RESTRICT"), nullable=False, index=True)
    campus_id: Mapped[str] = mapped_column(String(36), ForeignKey("campuses.id", ondelete="RESTRICT"), nullable=False, index=True)
    station_id: Mapped[str] = mapped_column(String(36), ForeignKey("stations.id", ondelete="RESTRICT"), nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    target_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    forecast_horizon_hours: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    predicted_pm2_5: Mapped[float] = mapped_column(Float, nullable=False)
    ci_lower: Mapped[float] = mapped_column(Float, nullable=False)
    ci_upper: Mapped[float] = mapped_column(Float, nullable=False)
    interval_confidence: Mapped[float] = mapped_column(Float, default=0.90, nullable=False)
    interval_method: Mapped[str] = mapped_column(String(50), default="residual_bootstrap", nullable=False)
    input_feature_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    input_quality_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    input_freshness_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    actual_pm2_5: Mapped[float] = mapped_column(Float, nullable=True)
    actual_observation_id: Mapped[str] = mapped_column(String(36), ForeignKey("observations.id", ondelete="SET NULL"), nullable=True)
    reconciled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    absolute_error: Mapped[float] = mapped_column(Float, nullable=True)
    signed_error: Mapped[float] = mapped_column(Float, nullable=True)
    squared_error: Mapped[float] = mapped_column(Float, nullable=True)
    trigger_level: Mapped[str] = mapped_column(String(50), default="good_or_acceptable", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="generated", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("model_run_id", "station_id", "target_timestamp", name="uq_pred_run_station_target"),
    )


class ModelExplanation(Base):
    __tablename__ = "model_explanations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("model_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_id: Mapped[str] = mapped_column(String(36), ForeignKey("predictions.id", ondelete="CASCADE"), nullable=True, index=True)
    explanation_scope: Mapped[str] = mapped_column(String(50), default="global", nullable=False)  # global, local_prediction, validation_summary
    explanation_method: Mapped[str] = mapped_column(String(50), default="shap_tree", nullable=False)
    campus_id: Mapped[str] = mapped_column(String(36), ForeignKey("campuses.id", ondelete="CASCADE"), nullable=False)
    station_id: Mapped[str] = mapped_column(String(36), ForeignKey("stations.id", ondelete="CASCADE"), nullable=False)
    forecast_horizon_hours: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    feature_value: Mapped[float] = mapped_column(Float, nullable=True)
    contribution_value: Mapped[float] = mapped_column(Float, nullable=False)
    absolute_contribution: Mapped[float] = mapped_column(Float, nullable=False)
    feature_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_value: Mapped[float] = mapped_column(Float, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ModelPromotionEvent(Base):
    __tablename__ = "model_promotion_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("model_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_model_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("model_runs.id", ondelete="SET NULL"), nullable=True)
    campus_id: Mapped[str] = mapped_column(String(36), ForeignKey("campuses.id", ondelete="CASCADE"), nullable=False)
    station_id: Mapped[str] = mapped_column(String(36), ForeignKey("stations.id", ondelete="CASCADE"), nullable=False)
    forecast_horizon_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # nominated, promoted, rejected, rolled_back, retired
    actor: Mapped[str] = mapped_column(String(100), default="admin", nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    metric_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ExternalComparison(Base):
    __tablename__ = "external_comparisons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campus_id: Mapped[str] = mapped_column(String(36), ForeignKey("campuses.id", ondelete="CASCADE"), nullable=False, index=True)
    station_id: Mapped[str] = mapped_column(String(36), ForeignKey("stations.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp_bucket: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    prediction_id: Mapped[str] = mapped_column(String(36), ForeignKey("predictions.id", ondelete="SET NULL"), nullable=True)
    airsense_prediction: Mapped[float] = mapped_column(Float, nullable=True)
    onsite_actual_pm2_5: Mapped[float] = mapped_column(Float, nullable=True)
    open_meteo_pm2_5: Mapped[float] = mapped_column(Float, nullable=True)
    openweather_pm2_5: Mapped[float] = mapped_column(Float, nullable=True)
    openaq_pm2_5: Mapped[float] = mapped_column(Float, nullable=True)
    waqi_value: Mapped[float] = mapped_column(Float, nullable=True)
    waqi_value_type: Mapped[str] = mapped_column(String(50), default="aqi_index", nullable=True)
    iqair_value: Mapped[float] = mapped_column(Float, nullable=True)
    iqair_value_type: Mapped[str] = mapped_column(String(50), default="aqi_index", nullable=True)
    source_timestamps_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source_ages_minutes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source_units_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source_statuses_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source_distances_km_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    comparable_errors_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    matching_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("station_id", "timestamp_bucket", name="uq_ext_comp_station_bucket"),
    )


class EvaluationEvent(Base):
    __tablename__ = "evaluation_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campus_id: Mapped[str] = mapped_column(String(36), ForeignKey("campuses.id", ondelete="CASCADE"), nullable=False, index=True)
    station_id: Mapped[str] = mapped_column(String(36), ForeignKey("stations.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_id: Mapped[str] = mapped_column(String(36), ForeignKey("predictions.id", ondelete="SET NULL"), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    target_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pm25_threshold, high_risk_combined, cleansing_rain
    forecast_pm2_5: Mapped[float] = mapped_column(Float, nullable=False)
    ci_lower: Mapped[float] = mapped_column(Float, nullable=False)
    ci_upper: Mapped[float] = mapped_column(Float, nullable=False)
    wind_speed_m_s: Mapped[float] = mapped_column(Float, nullable=True)
    rain_flag: Mapped[bool] = mapped_column(Boolean, nullable=True)
    level: Mapped[str] = mapped_column(String(50), nullable=False)  # good_or_acceptable, moderate, unhealthy, hazardous
    evaluation_mode: Mapped[str] = mapped_column(String(50), default="pilot_evaluation_only", nullable=False)
    actual_pm2_5: Mapped[float] = mapped_column(Float, nullable=True)
    outcome: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, true_positive, false_positive, missed, indeterminate
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(100), nullable=True)
    review_notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
