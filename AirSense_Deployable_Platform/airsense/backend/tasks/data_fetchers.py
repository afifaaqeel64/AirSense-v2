"""
AirSense Data Fetchers — All real-time data source integrations.
Each task: fetch → validate → insert → check threshold → maybe trigger retrain.
"""
import asyncio
import time
import httpx
from datetime import datetime, timedelta
from typing import Optional
from tasks.celery_app import app
from app.core.config import settings
from app.core.validator import validate_and_normalize
from app.core.metrics import MEASUREMENTS_INGESTED, FETCH_ERRORS, DATA_QUALITY
import structlog

log = structlog.get_logger()

# ── HELPERS ──────────────────────────────────────────────────

def _run_async(coro):
    """Run async code inside a Celery sync task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

async def _insert_and_log(records: list, source: str, city: str = "lahore"):
    from app.db.timescale import bulk_insert_measurements, log_ingestion
    start = time.time()
    if not records:
        await log_ingestion(source, city, 0, 0, 0)
        return 0
    inserted = await bulk_insert_measurements(records)
    duration = int((time.time() - start) * 1000)
    await log_ingestion(source, city, len(records), inserted, duration)
    MEASUREMENTS_INGESTED.labels(source=source, city=city).inc(inserted)
    avg_q = sum(r.get("data_quality_score", 1.0) for r in records) / len(records)
    DATA_QUALITY.labels(source=source, city=city).set(avg_q)
    log.info("data_ingested", source=source, city=city, records=inserted)
    return inserted

# ── WAQI (World Air Quality Index) ───────────────────────────

WAQI_LAHORE_STATIONS = {
    "lahore_us_consulate":   "@7165",
    "lahore_punjab_epa":     "@A316285",
    "lahore_gulberg":        "@A298761",
    "lahore_johar_town":     "@A316286",
    "lahore_dha_phase5":     "@A362621",
}

@app.task(bind=True, max_retries=3, default_retry_delay=300, name="tasks.data_fetchers.fetch_waqi_lahore")
def fetch_waqi_lahore(self):
    async def _fetch():
        records = []
        async with httpx.AsyncClient(timeout=15) as client:
            for station_id, waqi_id in WAQI_LAHORE_STATIONS.items():
                try:
                    url = f"https://api.waqi.info/feed/{waqi_id}/?token={settings.WAQI_TOKEN}"
                    r = await client.get(url)
                    data = r.json()
                    if data.get("status") != "ok":
                        continue
                    d = data["data"]
                    iaqi = d.get("iaqi", {})
                    record = validate_and_normalize({
                        "source": "waqi", "station_id": station_id, "city": "lahore",
                        "timestamp": datetime.utcnow(),
                        "aqi":         d.get("aqi"),
                        "pm25":        iaqi.get("pm25", {}).get("v"),
                        "pm10":        iaqi.get("pm10", {}).get("v"),
                        "no2":         iaqi.get("no2",  {}).get("v"),
                        "so2":         iaqi.get("so2",  {}).get("v"),
                        "co":          iaqi.get("co",   {}).get("v"),
                        "o3":          iaqi.get("o3",   {}).get("v"),
                        "temperature": iaqi.get("t",    {}).get("v"),
                        "humidity":    iaqi.get("h",    {}).get("v"),
                        "wind_speed":  iaqi.get("w",    {}).get("v"),
                        "pressure":    iaqi.get("p",    {}).get("v"),
                        "lat":         d["city"]["geo"][0] if d.get("city",{}).get("geo") else None,
                        "lon":         d["city"]["geo"][1] if d.get("city",{}).get("geo") else None,
                    })
                    records.append(record)
                    # Run alert checks for each reading
                    from app.services.alert_service import check_and_send_alerts
                    await check_and_send_alerts(record)
                except Exception as e:
                    FETCH_ERRORS.labels(source="waqi", city="lahore").inc()
                    log.error("waqi_station_failed", station=station_id, error=str(e))
        return await _insert_and_log(records, "waqi")
    try:
        count = _run_async(_fetch())
        check_data_threshold.delay(city="lahore")
        return {"source": "waqi", "inserted": count}
    except Exception as exc:
        FETCH_ERRORS.labels(source="waqi", city="lahore").inc()
        raise self.retry(exc=exc)

# ── OPENAQ ───────────────────────────────────────────────────

@app.task(bind=True, max_retries=3, default_retry_delay=300, name="tasks.data_fetchers.fetch_openaq_lahore")
def fetch_openaq_lahore(self):
    async def _fetch():
        records = []
        since = (datetime.utcnow() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        async with httpx.AsyncClient(timeout=30) as client:
            page = 1
            while page <= 5:
                try:
                    r = await client.get(
                        "https://api.openaq.org/v3/measurements",
                        params={"city": "Lahore", "country_id": "PK", "limit": 500,
                                "date_from": since, "page": page},
                        headers={"X-API-Key": settings.OPENAQ_API_KEY},
                    )
                    data = r.json()
                    results = data.get("results", [])
                    if not results:
                        break
                    for m in results:
                        record = validate_and_normalize({
                            "source": "openaq", "city": "lahore",
                            "station_id": m.get("locationId"),
                            "timestamp": m.get("date", {}).get("utc", datetime.utcnow().isoformat()),
                            m.get("parameter"): m.get("value"),
                            "lat": m.get("coordinates", {}).get("latitude"),
                            "lon": m.get("coordinates", {}).get("longitude"),
                        })
                        records.append(record)
                    page += 1
                except Exception as e:
                    FETCH_ERRORS.labels(source="openaq", city="lahore").inc()
                    log.error("openaq_page_failed", page=page, error=str(e))
                    break
        return await _insert_and_log(records, "openaq")
    try:
        count = _run_async(_fetch())
        return {"source": "openaq", "inserted": count}
    except Exception as exc:
        raise self.retry(exc=exc)

# ── IQAIR ────────────────────────────────────────────────────

@app.task(bind=True, max_retries=3, default_retry_delay=300, name="tasks.data_fetchers.fetch_iqair_lahore")
def fetch_iqair_lahore(self):
    async def _fetch():
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                "https://api.airvisual.com/v2/city",
                params={"city": "Lahore", "state": "Punjab",
                        "country": "Pakistan", "key": settings.IQAIR_API_KEY},
            )
            data = r.json()
            if data.get("status") != "success":
                return 0
            current = data["data"]["current"]
            pollution = current.get("pollution", {})
            weather   = current.get("weather", {})
            record = validate_and_normalize({
                "source": "iqair", "station_id": "lahore_iqair_city", "city": "lahore",
                "timestamp": pollution.get("ts", datetime.utcnow().isoformat()),
                "aqi":         pollution.get("aqius"),
                "pm25":        pollution.get("p2", {}).get("conc"),
                "pm10":        pollution.get("p1", {}).get("conc"),
                "temperature": weather.get("tp"),
                "humidity":    weather.get("hu"),
                "wind_speed":  weather.get("ws"),
                "wind_direction": weather.get("wd"),
                "pressure":    weather.get("pr"),
                "lat": data["data"]["location"]["coordinates"][1],
                "lon": data["data"]["location"]["coordinates"][0],
            })
            return await _insert_and_log([record], "iqair")
    try:
        return {"source": "iqair", "inserted": _run_async(_fetch())}
    except Exception as exc:
        raise self.retry(exc=exc)

# ── OPENWEATHERMAP ───────────────────────────────────────────

@app.task(bind=True, max_retries=3, name="tasks.data_fetchers.fetch_owm_lahore")
def fetch_owm_lahore(self):
    async def _fetch():
        async with httpx.AsyncClient(timeout=15) as client:
            # Air pollution
            ap = await client.get("https://api.openweathermap.org/data/2.5/air_pollution",
                                   params={"lat": 31.5497, "lon": 74.3436, "appid": settings.OWM_API_KEY})
            # Weather
            wth = await client.get("https://api.openweathermap.org/data/2.5/weather",
                                    params={"lat": 31.5497, "lon": 74.3436,
                                            "appid": settings.OWM_API_KEY, "units": "metric"})
            ap_data  = ap.json().get("list", [{}])[0]
            wth_data = wth.json()
            record = validate_and_normalize({
                "source": "openweathermap", "station_id": "lahore_owm", "city": "lahore",
                "timestamp": datetime.utcnow(),
                "pm25":  ap_data.get("components", {}).get("pm2_5"),
                "pm10":  ap_data.get("components", {}).get("pm10"),
                "no2":   ap_data.get("components", {}).get("no2"),
                "o3":    ap_data.get("components", {}).get("o3"),
                "so2":   ap_data.get("components", {}).get("so2"),
                "co":    ap_data.get("components", {}).get("co"),
                "nh3":   ap_data.get("components", {}).get("nh3"),
                "temperature":    wth_data.get("main", {}).get("temp"),
                "humidity":       wth_data.get("main", {}).get("humidity"),
                "pressure":       wth_data.get("main", {}).get("pressure"),
                "wind_speed":     wth_data.get("wind", {}).get("speed"),
                "wind_direction": wth_data.get("wind", {}).get("deg"),
                "lat": 31.5497, "lon": 74.3436,
            })
            return await _insert_and_log([record], "openweathermap")
    try:
        return {"source": "owm", "inserted": _run_async(_fetch())}
    except Exception as exc:
        raise self.retry(exc=exc)

# ── NASA FIRMS (Fire hotspots for crop burning PM2.5) ────────

@app.task(name="tasks.data_fetchers.fetch_nasa_firms")
def fetch_nasa_firms():
    async def _fetch():
        bbox = "73.9,31.2,74.7,31.8"  # Lahore bbox
        url  = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{settings.NASA_FIRMS_KEY}/MODIS_NRT/{bbox}/1"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return 0
            lines = r.text.strip().split("\n")
            records = []
            for line in lines[1:]:
                parts = line.split(",")
                if len(parts) < 9:
                    continue
                try:
                    record = validate_and_normalize({
                        "source": "nasa_firms", "city": "lahore",
                        "station_id": f"fire_{parts[0]}_{parts[1]}",
                        "timestamp": datetime.utcnow(),
                        "lat": float(parts[0]), "lon": float(parts[1]),
                        "fire_radiative_power": float(parts[8]) if parts[8] else None,
                    })
                    records.append(record)
                except Exception:
                    continue
            return await _insert_and_log(records, "nasa_firms")
    return {"source": "nasa_firms", "inserted": _run_async(_fetch())}

# ── SENTINEL-5P (Satellite NO2/SO2/CO/O3) ───────────────────

@app.task(name="tasks.data_fetchers.fetch_sentinel5p")
def fetch_sentinel5p():
    """
    Fetch Sentinel-5P tropospheric column data via Copernicus Dataspace.
    Provides NO2, SO2, CO, O3 over Lahore bounding box.
    """
    async def _fetch():
        # Use Copernicus OData API to get latest Sentinel-5P product
        bbox_wkt = "POLYGON((73.9 31.2, 74.7 31.2, 74.7 31.8, 73.9 31.8, 73.9 31.2))"
        url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
        params = {
            "$filter": (f"Collection/Name eq 'SENTINEL-5P' and "
                       f"contains(Name,'L2__NO2') and "
                       f"OData.CSC.Intersects(area=geography'SRID=4326;{bbox_wkt}')"),
            "$orderby": "ContentDate/Start desc",
            "$top": 1
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params=params)
            products = r.json().get("value", [])
            if products:
                log.info("sentinel5p_product_found", name=products[0].get("Name"),
                         date=products[0].get("ContentDate", {}).get("Start"))
            # In production: download product, process NetCDF, extract pixel values
            # For now we record that a satellite pass was detected
            record = validate_and_normalize({
                "source": "sentinel5p", "city": "lahore",
                "station_id": "sentinel5p_overpass",
                "timestamp": datetime.utcnow(),
                "lat": 31.5497, "lon": 74.3436,
            })
            return await _insert_and_log([record], "sentinel5p")
    return {"source": "sentinel5p", "inserted": _run_async(_fetch())}

# ── THRESHOLD CHECK & RETRAIN TRIGGER ────────────────────────

@app.task(name="tasks.data_fetchers.check_data_threshold")
def check_data_threshold(city: str = "lahore"):
    async def _check():
        from app.db.timescale import count_new_records_since_last_train
        new = await count_new_records_since_last_train(city)
        log.info("threshold_check", city=city, new_records=new,
                 threshold=settings.RETRAIN_THRESHOLD_RECORDS)
        if new >= settings.RETRAIN_THRESHOLD_RECORDS:
            trigger_retraining_task.delay(city=city, reason="data_threshold", new_records=new)
            return {"triggered": True, "records": new}
        return {"triggered": False, "records": new}
    return _run_async(_check())

@app.task(name="tasks.data_fetchers.check_and_trigger_retraining")
def check_and_trigger_retraining():
    """Scheduled: also trigger if 24h have elapsed regardless of record count."""
    async def _check():
        from app.db.timescale import get_conn
        conn = await get_conn()
        try:
            last_train = await conn.fetchval("""
                SELECT completed_at FROM ml_training_log
                WHERE status='success' ORDER BY completed_at DESC LIMIT 1
            """)
            hours_since = 999 if not last_train else (
                (datetime.utcnow() - last_train.replace(tzinfo=None)).total_seconds() / 3600
            )
            if hours_since >= settings.RETRAIN_MAX_INTERVAL_HOURS:
                trigger_retraining_task.delay(city="lahore", reason="scheduled_24h")
                return {"triggered": True, "reason": "24h_elapsed"}
        finally:
            await conn.close()
        check_data_threshold.delay(city="lahore")
        return {"triggered": False}
    return _run_async(_check())

@app.task(name="tasks.data_fetchers.trigger_retraining_task")
def trigger_retraining_task(city: str = "lahore", reason: str = "manual", new_records: int = 0):
    """Trigger the full ML retraining pipeline via Airflow REST API."""
    import httpx
    try:
        resp = httpx.post(
            "http://airflow-webserver:8080/api/v1/dags/airsense_model_retrain/dagRuns",
            json={"conf": {"city": city, "reason": reason, "new_records": new_records}},
            auth=("airflow", "airflow"),
            timeout=10
        )
        log.info("retrain_triggered", city=city, reason=reason,
                 status=resp.status_code, dag_run=resp.json().get("dag_run_id"))
        return {"triggered": True, "city": city, "reason": reason}
    except Exception as e:
        log.error("retrain_trigger_failed", error=str(e))
        # Fallback: run inline if Airflow unavailable
        from tasks.ml_pipeline import run_full_pipeline
        run_full_pipeline.delay(city=city)
        return {"triggered": True, "fallback": True}

@app.task(name="tasks.data_fetchers.run_alert_checks")
def run_alert_checks():
    async def _check():
        from app.db.timescale import get_current_aqi
        from app.services.alert_service import check_and_send_alerts
        readings = await get_current_aqi("lahore")
        for r in readings:
            await check_and_send_alerts(dict(r))
    return _run_async(_check())
