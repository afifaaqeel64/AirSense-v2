-- ============================================================
-- AirSense Database Initialization
-- TimescaleDB + PostgreSQL Schema
-- ============================================================

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- STATIONS
CREATE TABLE IF NOT EXISTS stations (
    id          VARCHAR(100) PRIMARY KEY,
    city        VARCHAR(50) NOT NULL,
    name        VARCHAR(200) NOT NULL,
    source      VARCHAR(50) NOT NULL,
    lat         DOUBLE PRECISION NOT NULL,
    lon         DOUBLE PRECISION NOT NULL,
    area_type   VARCHAR(50),
    is_active   BOOLEAN DEFAULT TRUE,
    added_at    TIMESTAMPTZ DEFAULT NOW(),
    metadata    JSONB DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_stations_city ON stations(city);

-- CORE MEASUREMENTS
CREATE TABLE IF NOT EXISTS measurements (
    id          BIGSERIAL,
    timestamp   TIMESTAMPTZ NOT NULL,
    city        VARCHAR(50) NOT NULL DEFAULT 'lahore',
    station_id  VARCHAR(100),
    source      VARCHAR(50) NOT NULL,
    pm25        FLOAT, pm10 FLOAT, no2 FLOAT, so2 FLOAT, co FLOAT, o3 FLOAT, nh3 FLOAT,
    aqi         INTEGER, aqi_category VARCHAR(50),
    temperature FLOAT, humidity FLOAT, wind_speed FLOAT, wind_direction FLOAT, pressure FLOAT,
    aod         FLOAT, no2_col FLOAT, fire_radiative_power FLOAT,
    lat         DOUBLE PRECISION, lon DOUBLE PRECISION,
    data_quality_score FLOAT DEFAULT 1.0,
    pm25_flagged BOOLEAN DEFAULT FALSE,
    is_interpolated BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (id, timestamp)
);

SELECT create_hypertable('measurements','timestamp',chunk_time_interval=>INTERVAL '7 days',if_not_exists=>TRUE);
CREATE INDEX IF NOT EXISTS idx_meas_city_time ON measurements(city, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_meas_station   ON measurements(station_id, timestamp DESC);

ALTER TABLE measurements SET (timescaledb.compress, timescaledb.compress_segmentby='city,station_id');
SELECT add_compression_policy('measurements', INTERVAL '30 days', if_not_exists=>TRUE);
SELECT add_retention_policy('measurements', INTERVAL '3 years', if_not_exists=>TRUE);

-- HOURLY AGGREGATE
CREATE MATERIALIZED VIEW IF NOT EXISTS measurements_hourly
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour',timestamp) AS hour, city, station_id,
    AVG(pm25) AS pm25, AVG(pm10) AS pm10, AVG(no2) AS no2, AVG(so2) AS so2,
    AVG(aqi) AS aqi, MAX(aqi) AS aqi_max,
    AVG(temperature) AS temperature, AVG(humidity) AS humidity,
    AVG(wind_speed) AS wind_speed, COUNT(*) AS reading_count
FROM measurements WHERE city IS NOT NULL
GROUP BY hour, city, station_id WITH NO DATA;

SELECT add_continuous_aggregate_policy('measurements_hourly',
    start_offset=>INTERVAL '3 hours', end_offset=>INTERVAL '30 minutes',
    schedule_interval=>INTERVAL '30 minutes', if_not_exists=>TRUE);

-- DAILY AGGREGATE
CREATE MATERIALIZED VIEW IF NOT EXISTS measurements_daily
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day',timestamp) AS day, city,
    AVG(pm25) AS pm25_avg, MAX(pm25) AS pm25_max, MIN(pm25) AS pm25_min,
    AVG(pm10) AS pm10_avg, AVG(no2) AS no2_avg, AVG(so2) AS so2_avg,
    AVG(aqi) AS aqi_avg, MAX(aqi) AS aqi_max, MIN(aqi) AS aqi_min,
    AVG(temperature) AS temp_avg, AVG(humidity) AS humidity_avg, COUNT(*) AS reading_count
FROM measurements GROUP BY day, city WITH NO DATA;

SELECT add_continuous_aggregate_policy('measurements_daily',
    start_offset=>INTERVAL '2 days', end_offset=>INTERVAL '1 hour',
    schedule_interval=>INTERVAL '1 hour', if_not_exists=>TRUE);

-- ML TRAINING LOG
CREATE TABLE IF NOT EXISTS ml_training_log (
    id          SERIAL PRIMARY KEY,
    run_id      VARCHAR(100) UNIQUE NOT NULL,
    model_name  VARCHAR(100) NOT NULL,
    model_version VARCHAR(20),
    city        VARCHAR(50) NOT NULL,
    triggered_by VARCHAR(50),
    new_records INTEGER, training_rows INTEGER, feature_count INTEGER,
    cv_rmse FLOAT, cv_mae FLOAT, cv_r2 FLOAT, prod_rmse FLOAT,
    promoted BOOLEAN DEFAULT FALSE,
    started_at TIMESTAMPTZ DEFAULT NOW(), completed_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'running', error_message TEXT,
    metadata JSONB DEFAULT '{}'
);

-- INGESTION LOG
CREATE TABLE IF NOT EXISTS ingestion_log (
    id              BIGSERIAL,
    source          VARCHAR(50) NOT NULL,
    city            VARCHAR(50) NOT NULL,
    fetched_at      TIMESTAMPTZ DEFAULT NOW(),
    records_fetched INTEGER DEFAULT 0, records_inserted INTEGER DEFAULT 0,
    duration_ms     INTEGER, status VARCHAR(20) DEFAULT 'success', error_message TEXT,
    PRIMARY KEY (id, fetched_at)
);
SELECT create_hypertable('ingestion_log','fetched_at',if_not_exists=>TRUE);
SELECT add_retention_policy('ingestion_log', INTERVAL '90 days', if_not_exists=>TRUE);

-- USERS
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255),
    full_name       VARCHAR(100),
    city            VARCHAR(50) DEFAULT 'lahore',
    role            VARCHAR(20) DEFAULT 'user',
    api_key         VARCHAR(64) UNIQUE,
    is_active       BOOLEAN DEFAULT TRUE,
    is_verified     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    preferences     JSONB DEFAULT '{"units":"us","language":"en","notifications":true}'
);
CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);

-- ALERT SUBSCRIPTIONS
CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id              SERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    city            VARCHAR(50) NOT NULL DEFAULT 'lahore',
    station_id      VARCHAR(100),
    threshold_aqi   INTEGER NOT NULL DEFAULT 150,
    channel         VARCHAR(20) NOT NULL,
    contact_info    VARCHAR(255) NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    last_alerted_at TIMESTAMPTZ,
    cooldown_hours  INTEGER DEFAULT 4,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- PREDICTIONS
CREATE TABLE IF NOT EXISTS predictions (
    id              BIGSERIAL,
    timestamp       TIMESTAMPTZ NOT NULL,
    city            VARCHAR(50) NOT NULL,
    model_name      VARCHAR(100),
    model_version   VARCHAR(20),
    prediction_for  TIMESTAMPTZ NOT NULL,
    predicted_aqi   FLOAT, predicted_pm25 FLOAT,
    confidence      FLOAT, horizon_hours INTEGER,
    PRIMARY KEY (id, timestamp)
);
SELECT create_hypertable('predictions','timestamp',if_not_exists=>TRUE);
SELECT add_retention_policy('predictions', INTERVAL '30 days', if_not_exists=>TRUE);

-- ANOMALIES
CREATE TABLE IF NOT EXISTS anomalies (
    id              BIGSERIAL,
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    city            VARCHAR(50) NOT NULL,
    station_id      VARCHAR(100),
    parameter       VARCHAR(50),
    observed_value  FLOAT, expected_value FLOAT, anomaly_score FLOAT,
    severity        VARCHAR(20), is_acknowledged BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (id, detected_at)
);
SELECT create_hypertable('anomalies','detected_at',if_not_exists=>TRUE);

-- AQI AUTO-CALCULATION FUNCTION
CREATE OR REPLACE FUNCTION calculate_aqi_pm25(pm25_value FLOAT) RETURNS INTEGER AS $$
DECLARE aqi INTEGER;
BEGIN
    IF pm25_value IS NULL THEN RETURN NULL; END IF;
    IF    pm25_value <=  12.0 THEN aqi := ROUND(4.166  * pm25_value);
    ELSIF pm25_value <=  35.4 THEN aqi := ROUND(2.103  * (pm25_value - 12.1) + 51);
    ELSIF pm25_value <=  55.4 THEN aqi := ROUND(2.459  * (pm25_value - 35.5) + 101);
    ELSIF pm25_value <= 150.4 THEN aqi := ROUND(0.516  * (pm25_value - 55.5) + 151);
    ELSIF pm25_value <= 250.4 THEN aqi := ROUND(0.990  * (pm25_value - 150.5) + 201);
    ELSIF pm25_value <= 350.4 THEN aqi := ROUND(0.990  * (pm25_value - 250.5) + 301);
    ELSIF pm25_value <= 500.4 THEN aqi := ROUND(0.648  * (pm25_value - 350.5) + 401);
    ELSE aqi := 500;
    END IF;
    RETURN GREATEST(0, LEAST(500, aqi));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION auto_calculate_aqi() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.pm25 IS NOT NULL AND NEW.aqi IS NULL THEN
        NEW.aqi := calculate_aqi_pm25(NEW.pm25);
    END IF;
    IF NEW.aqi IS NOT NULL THEN
        NEW.aqi_category := CASE
            WHEN NEW.aqi <=  50 THEN 'Good'
            WHEN NEW.aqi <= 100 THEN 'Moderate'
            WHEN NEW.aqi <= 150 THEN 'Unhealthy for Sensitive Groups'
            WHEN NEW.aqi <= 200 THEN 'Unhealthy'
            WHEN NEW.aqi <= 300 THEN 'Very Unhealthy'
            ELSE 'Hazardous'
        END;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_auto_aqi ON measurements;
CREATE TRIGGER trg_auto_aqi BEFORE INSERT ON measurements
    FOR EACH ROW EXECUTE FUNCTION auto_calculate_aqi();

-- VIEWS
CREATE OR REPLACE VIEW latest_station_readings AS
SELECT DISTINCT ON (city, station_id)
    city, station_id, source, timestamp,
    pm25, pm10, no2, so2, co, o3,
    aqi, aqi_category, temperature, humidity,
    wind_speed, wind_direction, lat, lon, data_quality_score
FROM measurements
WHERE timestamp > NOW() - INTERVAL '2 hours'
ORDER BY city, station_id, timestamp DESC;

CREATE OR REPLACE VIEW city_current_summary AS
SELECT
    city,
    ROUND(AVG(aqi))::INTEGER AS avg_aqi,
    MAX(aqi) AS max_aqi,
    ROUND(AVG(pm25)::NUMERIC,1) AS avg_pm25,
    COUNT(DISTINCT station_id) AS active_stations,
    MAX(timestamp) AS last_updated
FROM latest_station_readings GROUP BY city;

CREATE OR REPLACE VIEW pipeline_health AS
SELECT source, city,
    MAX(fetched_at) AS last_fetch,
    EXTRACT(EPOCH FROM (NOW() - MAX(fetched_at)))/60 AS minutes_ago,
    ROUND(AVG(CASE WHEN status='success' THEN 1.0 ELSE 0.0 END)*100,1) AS success_rate,
    SUM(records_inserted) AS records_today
FROM ingestion_log WHERE fetched_at > NOW() - INTERVAL '24 hours'
GROUP BY source, city ORDER BY minutes_ago DESC;

-- SEED LAHORE STATIONS
INSERT INTO stations (id,city,name,source,lat,lon,area_type) VALUES
    ('lahore_us_consulate',  'lahore','US Consulate Lahore',        'waqi',      31.5204,74.3587,'urban'),
    ('lahore_punjab_epa',    'lahore','Punjab EPA Headquarters',    'waqi',      31.5167,74.3500,'urban'),
    ('lahore_gulberg',       'lahore','Gulberg III',                'waqi',      31.5120,74.3500,'residential'),
    ('lahore_johar_town',    'lahore','Johar Town',                 'waqi',      31.4697,74.2728,'residential'),
    ('lahore_dha_phase5',    'lahore','DHA Phase 5',                'waqi',      31.4812,74.4022,'residential'),
    ('lahore_kot_lakhpat',   'lahore','Kot Lakhpat Industrial',     'punjab_epa',31.5200,74.2700,'industrial'),
    ('lahore_township',      'lahore','Township',                   'punjab_epa',31.5000,74.2800,'residential'),
    ('lahore_model_town',    'lahore','Model Town',                 'punjab_epa',31.4800,74.3200,'residential'),
    ('lahore_wapda_town',    'lahore','Wapda Town',                 'punjab_epa',31.4600,74.3000,'residential'),
    ('lahore_shahdara',      'lahore','Shahdara Town',              'openaq',    31.5900,74.3200,'suburban'),
    ('lahore_mughalpura',    'lahore','Mughalpura Industrial',      'openaq',    31.5600,74.3900,'industrial'),
    ('lahore_ferozepur_rd',  'lahore','Ferozepur Road',             'openaq',    31.5100,74.3000,'traffic'),
    ('lahore_mall_road',     'lahore','Mall Road',                  'openaq',    31.5600,74.3500,'traffic'),
    ('lahore_airport',       'lahore','Allama Iqbal Airport',       'pakmet',    31.5216,74.4036,'background'),
    ('isb_us_embassy',   'islamabad','US Embassy Islamabad',        'waqi',      33.7294,73.0931,'urban'),
    ('isb_f8_markaz',    'islamabad','F-8 Markaz',                  'waqi',      33.7073,73.0479,'residential')
ON CONFLICT (id) DO NOTHING;

COMMIT;
