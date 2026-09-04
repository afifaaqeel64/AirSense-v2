"""AirSense Model Retraining DAG — event-driven, triggered by data watchdog."""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
import sys

DEFAULT_ARGS = {
    "owner": "airsense", "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=3),
}

def extract_features(**ctx):
    city = ctx["dag_run"].conf.get("city", "lahore")
    import asyncio, asyncpg
    sys.path.insert(0, "/opt/airsense/backend")
    from app.core.config import settings
    async def _get():
        conn = await asyncpg.connect(settings.DATABASE_URL.replace("postgresql+asyncpg://","postgresql://"))
        rows = await conn.fetch("""
            SELECT timestamp, city, pm25, pm10, no2, so2, co, o3,
                   aqi, temperature, humidity, wind_speed, wind_direction
            FROM measurements WHERE city=$1
              AND timestamp > NOW() - INTERVAL '90 days'
              AND data_quality_score >= 0.5 ORDER BY timestamp ASC
        """, city)
        await conn.close()
        return [dict(r) for r in rows]
    loop = asyncio.new_event_loop()
    records = loop.run_until_complete(_get())
    loop.close()
    ctx["ti"].xcom_push(key="record_count", value=len(records))
    ctx["ti"].xcom_push(key="city", value=city)
    return len(records)

def validate_data(**ctx):
    count = ctx["ti"].xcom_pull(key="record_count")
    if count < 100:
        raise ValueError(f"Insufficient data: {count} records")
    return True

def train_aqi(**ctx):
    city = ctx["ti"].xcom_pull(key="city") or "lahore"
    sys.path.insert(0, "/opt/airsense/backend")
    from tasks.ml_pipeline import _train_aqi_model
    return _train_aqi_model(city, ctx["run_id"])

def train_forecast(**ctx):
    city = ctx["ti"].xcom_pull(key="city") or "lahore"
    sys.path.insert(0, "/opt/airsense/backend")
    from tasks.ml_pipeline import _train_forecast_model
    return _train_forecast_model(city, ctx["run_id"])

def train_health(**ctx):
    city = ctx["ti"].xcom_pull(key="city") or "lahore"
    sys.path.insert(0, "/opt/airsense/backend")
    from tasks.ml_pipeline import _train_health_model
    return _train_health_model(city, ctx["run_id"])

def train_anomaly(**ctx):
    city = ctx["ti"].xcom_pull(key="city") or "lahore"
    sys.path.insert(0, "/opt/airsense/backend")
    from tasks.ml_pipeline import _train_anomaly_model
    return _train_anomaly_model(city, ctx["run_id"])

def notify_complete(**ctx):
    city = ctx["ti"].xcom_pull(key="city") or "lahore"
    print(f"Pipeline complete for {city} | run_id: {ctx['run_id']}")
    return "done"

with DAG(
    "airsense_model_retrain",
    default_args=DEFAULT_ARGS,
    description="Auto-retrain AirSense ML models",
    schedule_interval=None,
    start_date=days_ago(1),
    catchup=False, max_active_runs=1,
    tags=["ml","lahore","airsense"],
) as dag:
    start    = EmptyOperator(task_id="start")
    extract  = PythonOperator(task_id="extract_features",    python_callable=extract_features)
    validate = PythonOperator(task_id="validate_data",       python_callable=validate_data)
    t_aqi    = PythonOperator(task_id="train_aqi",           python_callable=train_aqi)
    t_fc     = PythonOperator(task_id="train_forecast",      python_callable=train_forecast)
    t_hl     = PythonOperator(task_id="train_health",        python_callable=train_health)
    t_an     = PythonOperator(task_id="train_anomaly",       python_callable=train_anomaly)
    done     = PythonOperator(task_id="notify",              python_callable=notify_complete, trigger_rule="all_done")
    end      = EmptyOperator(task_id="end")
    start >> extract >> validate >> [t_aqi, t_fc, t_hl, t_an] >> done >> end
