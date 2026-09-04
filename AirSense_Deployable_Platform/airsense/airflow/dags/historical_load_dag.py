"""One-time historical data load from OpenAQ for Lahore."""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
import sys

with DAG("airsense_historical_load", schedule_interval=None,
         start_date=days_ago(1), catchup=False, tags=["data","historical"]) as dag:

    def load_historical(**ctx):
        import asyncio, httpx
        sys.path.insert(0, "/opt/airsense/backend")
        from app.core.config import settings
        from app.core.validator import validate_and_normalize
        from app.db.timescale import bulk_insert_measurements

        async def _load():
            total = 0
            async with httpx.AsyncClient(timeout=60) as client:
                for page in range(1, 200):
                    r = await client.get("https://api.openaq.org/v3/measurements",
                        params={"city":"Lahore","country_id":"PK",
                                "date_from":"2018-01-01T00:00:00Z",
                                "limit":1000,"page":page},
                        headers={"X-API-Key": settings.OPENAQ_API_KEY})
                    results = r.json().get("results",[])
                    if not results: break
                    records = [validate_and_normalize({
                        "source":"openaq_historical","city":"lahore",
                        "station_id": m.get("locationId"),
                        "timestamp": m.get("date",{}).get("utc"),
                        m.get("parameter"): m.get("value"),
                        "lat": m.get("coordinates",{}).get("latitude"),
                        "lon": m.get("coordinates",{}).get("longitude"),
                    }) for m in results if m.get("parameter") and m.get("value") is not None]
                    inserted = await bulk_insert_measurements(records)
                    total += inserted
                    if page % 20 == 0: print(f"Page {page} — total: {total}")
            return total
        loop = asyncio.new_event_loop()
        total = loop.run_until_complete(_load())
        loop.close()
        print(f"Historical load complete: {total} records")
        return total

    PythonOperator(task_id="load_openaq_historical", python_callable=load_historical,
                   execution_timeout=timedelta(hours=12))
