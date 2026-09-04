
import sys, os, math, asyncio
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, delete

sys.path.insert(0, os.path.abspath('.'))

from services.quality_control.qc_engine import QualityControlEngine, compute_content_hash, PHYSICAL_LIMITS
from services.quality_control.gap_and_aggregation import calculate_circular_wind_mean, HourlyAggregationEngine
from apps.api.routers.ingest_router import ESP32IngestPayload, ESP32ReadingsSubschema
from apps.api.core.security import generate_secure_token, hash_token
from apps.api.main import app
from apps.api.db.session import engine, AsyncSessionLocal
from apps.api.db.models import Base, Campus, Station, Device, RawReading, Observation, QualityAssessment, HourlyObservation

passed = 0
failed = 0
total = 0

def test(name, cond, info=''):
    global passed, failed, total
    total += 1
    if cond:
        passed += 1
        print(f'  [PASS] {name} {info}')
    else:
        failed += 1
        print(f'  [FAIL] {name} {info}')

async def main():
    global passed, failed, total

    print('=' * 80)
    print('CHALLENGE SUITE 1: 6-STAGE SENSORY QUALITY CONTROL BOUNDARY CONDITIONS')
    print('=' * 80)

    # 1.1 Baseline Perfect Reading
    r = {'observed_at': datetime.now(timezone.utc), 'pm1': 10.0, 'pm2_5': 20.0, 'pm10': 35.0, 'temperature_c': 25.0, 'humidity_pct': 50.0, 'pressure_hpa': 1013.25}
    res = QualityControlEngine.evaluate_reading(r)
    test('1.1 Perfect Reading Accepted', res.quality_score == 1.0 and res.quality_status == 'accepted')
    test('1.1 Baseline Flags False', not any([res.impossible_value_flag, res.high_humidity_flag, res.spike_review_flag, res.ordering_consistency_flag, res.timestamp_flag]))

    # 1.2 Boundary: Negative PM2.5 (-10.0)
    res = QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'pm2_5': -10.0})
    test('1.2 Negative PM2.5 (-10.0) Impossible & Rejected', res.impossible_value_flag is True and res.quality_status == 'rejected')

    # 1.3 Boundary: Small Negative PM2.5 (-0.01)
    res = QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'pm2_5': -0.01})
    test('1.3 Small Negative PM2.5 (-0.01) Rejected', res.impossible_value_flag is True and res.quality_status == 'rejected')

    # 1.4 Boundary: Valid Zero Floor (0.0)
    res = QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'pm1': 0.0, 'pm2_5': 0.0, 'pm10': 0.0, 'temperature_c': 0.0, 'humidity_pct': 0.0, 'pressure_hpa': 1000.0})
    test('1.4 Valid Zero Floor (0.0)', res.impossible_value_flag is False and res.quality_status == 'accepted')

    # 1.5 Particulate Ordering: PM1 > PM2.5
    res = QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'pm1': 50.0, 'pm2_5': 30.0, 'pm10': 60.0})
    test('1.5 Ordering Violation PM1 > PM2.5', res.ordering_consistency_flag is True and res.quality_score == 0.75)

    # 1.6 Particulate Ordering: PM2.5 > PM10
    res = QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'pm1': 20.0, 'pm2_5': 60.0, 'pm10': 40.0})
    test('1.6 Ordering Violation PM2.5 > PM10', res.ordering_consistency_flag is True and res.quality_score == 0.75)

    # 1.7 Particulate Ordering: PM1 > PM2.5 > PM10 (Double Violation)
    res = QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'pm1': 80.0, 'pm2_5': 60.0, 'pm10': 40.0})
    test('1.7 Double Ordering Violation (PM1 > PM2.5 > PM10)', res.ordering_consistency_flag is True and res.quality_score == 0.50)

    # 1.8 Particulate Ordering Equality (PM1 == PM2.5 == PM10)
    res = QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'pm1': 25.0, 'pm2_5': 25.0, 'pm10': 25.0})
    test('1.8 Particle Ordering Equality (PM1=PM2.5=PM10)', res.ordering_consistency_flag is False and res.quality_score == 1.0)

    # 1.9 High Humidity: 90.0% vs 90.1% vs 95.0%
    res90 = QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'humidity_pct': 90.0})
    test('1.9 Humidity 90.0% (No Swelling Flag)', res90.high_humidity_flag is False and res90.quality_score == 1.0)

    res901 = QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'humidity_pct': 90.1})
    test('1.9 Humidity 90.1% (High Humidity Flag Triggered)', res901.high_humidity_flag is True and res901.quality_score == 0.85)

    res95 = QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'humidity_pct': 95.0})
    test('1.9 Humidity 95.0% (Warning State)', res95.high_humidity_flag is True and res95.quality_status == 'accepted_with_warning')

    # 1.10 Out-of-bounds Humidity (>100.0%)
    res105 = QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'humidity_pct': 105.0})
    test('1.10 Impossible Humidity (105%) Rejection', res105.impossible_value_flag is True and res105.quality_status == 'rejected')

    # 1.11 Extreme Particulate Spike (>150 ug/m3 delta)
    prev = {'pm2_5': 30.0}
    curr = {'observed_at': datetime.now(timezone.utc), 'pm2_5': 185.0}
    res_sp = QualityControlEngine.evaluate_reading(curr, previous_reading=prev)
    test('1.11 Extreme Spike (Delta=155.0)', res_sp.spike_review_flag is True and res_sp.quality_score == 0.80)

    # 1.12 Non-Spike Boundary (Delta = 150.0 exactly)
    curr150 = {'observed_at': datetime.now(timezone.utc), 'pm2_5': 180.0}
    res_sp150 = QualityControlEngine.evaluate_reading(curr150, previous_reading=prev)
    test('1.12 Delta exactly 150.0 (No Spike Flag)', res_sp150.spike_review_flag is False and res_sp150.quality_score == 1.0)

    # 1.13 Temperature Bounds (-20 to 60 C)
    test('1.13 Temp Min Valid (-20C)', QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'temperature_c': -20.0}).impossible_value_flag is False)
    test('1.13 Temp Below Min (-21C)', QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'temperature_c': -21.0}).impossible_value_flag is True)
    test('1.13 Temp Max Valid (60C)', QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'temperature_c': 60.0}).impossible_value_flag is False)
    test('1.13 Temp Above Max (61C)', QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'temperature_c': 61.0}).impossible_value_flag is True)

    # 1.14 Pressure Bounds (800 to 1100 hPa)
    test('1.14 Pressure Min Valid (800 hPa)', QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'pressure_hpa': 800.0}).impossible_value_flag is False)
    test('1.14 Pressure Below Min (799 hPa)', QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'pressure_hpa': 799.0}).impossible_value_flag is True)
    test('1.14 Pressure Max Valid (1100 hPa)', QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'pressure_hpa': 1100.0}).impossible_value_flag is False)
    test('1.14 Pressure Above Max (1101 hPa)', QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'pressure_hpa': 1101.0}).impossible_value_flag is True)

    # 1.15 Wind Speed Bounds (0 to 100 m/s)
    test('1.15 Wind Speed Min (0 m/s)', QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'wind_speed_m_s': 0.0}).impossible_value_flag is False)
    test('1.15 Wind Speed Negative (-1 m/s)', QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'wind_speed_m_s': -1.0}).impossible_value_flag is True)
    test('1.15 Wind Speed Max (100 m/s)', QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'wind_speed_m_s': 100.0}).impossible_value_flag is False)
    test('1.15 Wind Speed Above Max (101 m/s)', QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'wind_speed_m_s': 101.0}).impossible_value_flag is True)

    # 1.16 Timestamps: Future & Missing
    fut = datetime.now(timezone.utc) + timedelta(hours=2)
    test('1.16 Future Timestamp Flagged', QualityControlEngine.evaluate_reading({'observed_at': fut, 'pm2_5': 25.0}).timestamp_flag is True)
    test('1.16 Missing Timestamp Flagged', QualityControlEngine.evaluate_reading({'pm2_5': 25.0}).timestamp_flag is True)
    test('1.17 Non-numeric String Value Rejected', QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'pm2_5': 'invalid'}).impossible_value_flag is True)

    print('\n' + '=' * 80)
    print('CHALLENGE SUITE 2: CIRCULAR WIND DIRECTION CALCULATIONS ACROSS QUADRANTS')
    print('=' * 80)

    # 2.1 Crossing 359° and 1° -> 0.0° (North)
    test('2.1 Crossing 359 deg and 1 deg Mean = 0.0 deg', calculate_circular_wind_mean([359.0, 1.0]) == 0.0)

    # 2.2 Crossing 350° and 10° -> 0.0° (North)
    test('2.2 Crossing 350 deg and 10 deg Mean = 0.0 deg', calculate_circular_wind_mean([350.0, 10.0]) == 0.0)

    # 2.3 East Quadrant: [89°, 91°] -> 90.0°
    test('2.3 East [89 deg, 91 deg] Mean = 90.0 deg', calculate_circular_wind_mean([89.0, 91.0]) == 90.0)

    # 2.4 South Quadrant: [179°, 181°] -> 180.0°
    test('2.4 South [179 deg, 181 deg] Mean = 180.0 deg', calculate_circular_wind_mean([179.0, 181.0]) == 180.0)

    # 2.5 West Quadrant: [269°, 271°] -> 270.0°
    test('2.5 West [269 deg, 271 deg] Mean = 270.0 deg', calculate_circular_wind_mean([269.0, 271.0]) == 270.0)

    # 2.6 Diagonal [0°, 90°] -> 45.0°
    test('2.6 North-East [0 deg, 90 deg] Mean = 45.0 deg', calculate_circular_wind_mean([0.0, 90.0]) == 45.0)

    # 2.7 Symmetrical opposition [0°, 180°] -> 0.0°
    test('2.7 Symmetrical Opposition [0 deg, 180 deg] Fallback to 0.0 deg', calculate_circular_wind_mean([0.0, 180.0]) == 0.0)

    # 2.8 Edge: Empty and NaN
    test('2.8 Empty List -> None', calculate_circular_wind_mean([]) is None)
    test('2.8 NaN/None List -> None', calculate_circular_wind_mean([None, float('nan')]) is None)

    print('\n' + '=' * 80)
    print('CHALLENGE SUITE 3: INGESTION PIPELINE SCHEMAS, IDEMPOTENCY & AUTH')
    print('=' * 80)

    # 3.1 Content Hash Determinism & Sensitivity
    t0 = datetime(2026, 8, 19, 14, 30, 0, tzinfo=timezone.utc)
    h1 = compute_content_hash('ISB-CAMPUS-01', t0, 25.5, 28.0)
    h2 = compute_content_hash('ISB-CAMPUS-01', t0, 25.5, 28.0)
    h3 = compute_content_hash('ISB-CAMPUS-01', t0, 25.6, 28.0)
    test('3.1 Content Hash Deterministic', h1 == h2 and len(h1) == 64)
    test('3.2 Content Hash Perturbation Sensitive', h1 != h3)

    # 3.3 Canonical Schema Validation
    canon = {'schema_version': '1.0', 'device_uid': 'ESP32-01', 'station_code': 'ISB-01', 'pm1': 8.5, 'pm2_5': 14.2, 'pm10': 22.0, 'temperature': 28.5, 'humidity': 62.0, 'pressure': 1012.5, 'rain_flag': False, 'sequence_number': 1042}
    p_c = ESP32IngestPayload(**canon)
    test('3.3 Canonical Schema Parsing', p_c.pm2_5 == 14.2 and p_c.sequence_number == 1042)

    # 3.4 Legacy Nested Schema Validation
    legacy = {'device_id': 'ESP32-01', 'readings': {'pm1': 5.0, 'pm25': 12.0, 'pm10': 18.0, 'temperature': 24.0, 'humidity': 50.0, 'pressure': 1010.0, 'rain_flag': True}}
    p_l = ESP32IngestPayload(**legacy)
    test('3.4 Legacy Nested Schema Parsing', p_l.readings['pm25'] == 12.0 and p_l.readings['rain_flag'] is True)

    # 3.5 Token Generation and Salted SHA-256 Hashing
    tok = generate_secure_token()
    tok_h = hash_token(tok)
    test('3.5 Secure Token Generation', len(tok) >= 32 and tok.startswith('airsense_dev_'))
    test('3.5 Token Salted Hash Match', hash_token(tok) == tok_h)
    test('3.5 Token Salted Hash Mismatch on Forgery', hash_token('forged_token') != tok_h)

    print('\n' + '=' * 80)
    print('CHALLENGE SUITE 4: FASTAPI LIVE INGESTION API & END-TO-END VERIFICATION')
    print('=' * 80)

    # Seed test station and device in DB using existing campus if present
    test_raw_token = 'airsense_dev_stress_token_secret_9999'
    token_h = hash_token(test_raw_token)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check campus
        res_c = await session.execute(select(Campus).where(Campus.code == 'ISB_CAMPUS'))
        c = res_c.scalar_one_or_none()
        if not c:
            c = Campus(code='ISB_CAMPUS', name='Islamabad Campus', city='Islamabad', country='Pakistan', status='active', location_status='verified', contact_name='Test Admin')
            session.add(c)
            await session.flush()
        
        # Check station
        res_st = await session.execute(select(Station).where(Station.station_code == 'ISB-CAMPUS-01'))
        st = res_st.scalar_one_or_none()
        if not st:
            st = Station(campus_id=c.id, station_code='ISB-CAMPUS-01', station_name='Islamabad Main Station', installation_location='Rooftop')
            session.add(st)
            await session.flush()

        # Seed device with known token
        res_dev = await session.execute(select(Device).where(Device.device_uid == 'ESP32-AIRSENSE-ISB-01'))
        dev = res_dev.scalar_one_or_none()
        if not dev:
            dev = Device(station_id=st.id, device_uid='ESP32-AIRSENSE-ISB-01', token_hash=token_h, firmware_version='1.0.0', status='active')
            session.add(dev)
        else:
            dev.token_hash = token_h
            dev.status = 'active'
        await session.flush()

        # Clean up prior test readings for idempotent harness execution
        await session.execute(delete(Observation).where(Observation.station_id == st.id))
        await session.execute(delete(QualityAssessment).where(QualityAssessment.raw_reading_id.in_(
            select(RawReading.id).where(RawReading.station_id == st.id)
        )))
        await session.execute(delete(HourlyObservation).where(HourlyObservation.station_id == st.id))
        await session.execute(delete(RawReading).where(RawReading.station_id == st.id))
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        headers_bearer = {'Authorization': f'Bearer {test_raw_token}'}
        headers_x = {'X-Device-Token': test_raw_token}

        # 4.1 Ingestion Health Check
        res_h = await client.get('/api/v1/ingest/health')
        test('4.1 Ingestion Health Endpoint Status 200', res_h.status_code == 200 and res_h.json()['status'] == 'healthy')

        # 4.2 Valid Ingestion via Bearer Token
        payload_1 = {
            'schema_version': '1.0',
            'device_uid': 'ESP32-AIRSENSE-ISB-01',
            'station_code': 'ISB-CAMPUS-01',
            'timestamp': '2026-08-19T14:30:00Z',
            'pm1': 8.5,
            'pm2_5': 14.2,
            'pm10': 22.0,
            'temperature': 28.5,
            'humidity': 62.0,
            'pressure': 1012.5,
            'rain_flag': False,
            'sequence_number': 1001
        }
        res_ing1 = await client.post('/api/v1/ingest/reading', json=payload_1, headers=headers_bearer)
        test('4.2 Ingestion via Bearer Auth Status 200', res_ing1.status_code == 200)
        data1 = res_ing1.json()
        test('4.2 Ingestion Response Accepted', data1.get('accepted') is True and data1.get('duplicate') is False)
        test('4.2 Ingestion Response QC Status', data1.get('quality_processing_state') == 'accepted')

        # 4.3 Idempotent Duplicate Detection (Submitting exact same reading)
        res_ing2 = await client.post('/api/v1/ingest/reading', json=payload_1, headers=headers_x)
        test('4.3 Duplicate Reading Submission Status 200', res_ing2.status_code == 200)
        data2 = res_ing2.json()
        test('4.3 Duplicate Reading Flagged True', data2.get('accepted') is True and data2.get('duplicate') is True)
        test('4.3 Duplicate State duplicate_skipped', data2.get('quality_processing_state') == 'duplicate_skipped')
        test('4.3 Duplicate Returns Same Ingestion ID', data2.get('raw_reading_id') == data1.get('raw_reading_id'))

        # 4.4 Ingestion with Invalid Token -> 401
        res_inv = await client.post('/api/v1/ingest/reading', json=payload_1, headers={'Authorization': 'Bearer wrong_token_xyz'})
        test('4.4 Invalid Token Rejection 401', res_inv.status_code == 401)
        test('4.4 Error Detail Code INVALID_DEVICE_TOKEN', res_inv.json()['detail']['error']['code'] == 'INVALID_DEVICE_TOKEN')

        # 4.5 Ingestion with Missing Auth Header -> 401
        res_noauth = await client.post('/api/v1/ingest/reading', json=payload_1)
        test('4.5 Missing Auth Header Rejection 401', res_noauth.status_code == 401)
        test('4.5 Error Detail Code MISSING_DEVICE_TOKEN', res_noauth.json()['detail']['error']['code'] == 'MISSING_DEVICE_TOKEN')

        # 4.6 Ingestion of Impossible Negative PM2.5 via API
        payload_neg = {
            'schema_version': '1.0',
            'timestamp': '2026-08-19T14:31:00Z',
            'pm2_5': -10.0,
            'temperature': 28.0,
            'sequence_number': 1002
        }
        res_neg_api = await client.post('/api/v1/ingest/reading', json=payload_neg, headers=headers_bearer)
        test('4.6 Negative PM2.5 Ingestion Status 200', res_neg_api.status_code == 200)
        data_neg = res_neg_api.json()
        test('4.6 Negative PM2.5 Quality State rejected', data_neg.get('quality_processing_state') == 'rejected')

        # 4.7 Ingestion of High Humidity (>90%) with Rain Flag
        payload_rain = {
            'schema_version': '1.0',
            'timestamp': '2026-08-19T14:32:00Z',
            'pm1': 10.0,
            'pm2_5': 20.0,
            'pm10': 30.0,
            'temperature': 22.0,
            'humidity': 95.0,
            'rain_flag': True,
            'sequence_number': 1003
        }
        res_rain_api = await client.post('/api/v1/ingest/reading', json=payload_rain, headers=headers_bearer)
        test('4.7 High Humidity & Rain Ingestion Status 200', res_rain_api.status_code == 200)
        data_rain = res_rain_api.json()
        test('4.7 High Humidity Quality State accepted_with_warning', data_rain.get('quality_processing_state') == 'accepted_with_warning')

        # 4.8 Latest Readings Query Endpoint
        res_latest = await client.get('/api/v1/ingest/latest?limit=10')
        test('4.8 Latest Ingest Readings Status 200', res_latest.status_code == 200)
        latest_data = res_latest.json()
        test('4.8 Latest Readings Non-Empty', len(latest_data) >= 3)
        test('4.8 Latest Reading Schema Keys Present', all(k in latest_data[0] for k in ['id', 'station_id', 'observed_at', 'pm2_5', 'humidity_pct', 'rain_flag']))

        # 4.9 Corrupted Data Type (String for float) -> 422
        corrupted_payload = {
            'timestamp': '2026-08-19T14:35:00Z',
            'pm2_5': 'not_a_valid_float_number'
        }
        res_422 = await client.post('/api/v1/ingest/reading', json=corrupted_payload, headers=headers_bearer)
        test('4.9 Corrupted Type Rejection 422 Unprocessable Entity', res_422.status_code == 422)

    print('\n' + '=' * 80)
    print('FINAL EMPIRICAL RESULTS SUMMARY')
    print('=' * 80)
    print(f'Total Empirical Challenges: {total}')
    print(f'Passed: {passed}')
    print(f'Failed: {failed}')
    print(f'Success Rate: {(passed / total) * 100:.1f}%')

    if failed == 0:
        print('\n>>> ALL EMPIRICAL CHALLENGES PASSED! VERDICT: APPROVE <<<')
        sys.exit(0)
    else:
        print(f'\n>>> {failed} CHALLENGES FAILED! VERDICT: CHALLENGE_FAILED <<<')
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
