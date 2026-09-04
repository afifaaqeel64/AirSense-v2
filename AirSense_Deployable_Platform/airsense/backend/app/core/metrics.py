from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

REQUEST_COUNT = Counter(
    'airsense_http_requests_total', 'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)
REQUEST_LATENCY = Histogram(
    'airsense_http_request_duration_seconds', 'Request duration',
    ['endpoint'], buckets=[0.01,0.05,0.1,0.25,0.5,1.0,2.5,5.0]
)
MEASUREMENTS_INGESTED = Counter(
    'airsense_measurements_ingested_total', 'Measurements ingested',
    ['source', 'city']
)
DATA_QUALITY = Gauge(
    'airsense_data_quality_score', 'Data quality score',
    ['source', 'city']
)
MODEL_RMSE = Gauge(
    'airsense_model_rmse', 'Model RMSE metric',
    ['model_name', 'city']
)
MODEL_MAE = Gauge(
    'airsense_model_mae', 'Model MAE metric',
    ['model_name', 'city']
)
LAST_TRAIN_TS = Gauge(
    'airsense_last_training_unix', 'Unix timestamp of last training',
    ['model_name', 'city']
)
ACTIVE_WS_CONNECTIONS = Gauge(
    'airsense_websocket_connections', 'Active WebSocket connections'
)
CURRENT_AQI = Gauge(
    'airsense_current_aqi', 'Current AQI value',
    ['city', 'station_id']
)
FETCH_ERRORS = Counter(
    'airsense_fetch_errors_total', 'Data fetch errors',
    ['source', 'city']
)
RETRAIN_TRIGGERS = Counter(
    'airsense_retrain_triggers_total', 'Model retraining triggers',
    ['city', 'reason']
)

def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
