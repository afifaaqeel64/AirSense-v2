import sys
import os
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath('.'))

from services.quality_control.qc_engine import QualityControlEngine, compute_content_hash, PHYSICAL_LIMITS
from services.quality_control.gap_and_aggregation import calculate_circular_wind_mean, HourlyAggregationEngine
from apps.api.routers.ingest_router import ESP32IngestPayload, ESP32ReadingsSubschema
from apps.api.core.security import generate_secure_token, hash_token, verify_token


def run_all_challenges():
    passed = 0
    failed = 0
    total = 0

    def assert_test(name: str, condition: bool, details: str = ''):
        nonlocal passed, failed, total
        total += 1
        if condition:
            passed += 1
            print(f'  [PASS] {name} {details}')
        else:
            failed += 1
            print(f'  [FAIL] {name} {details}')

    print('=' * 80)
    print('CHALLENGE SUITE 1: 6-STAGE SENSORY QUALITY CONTROL ENGINE BOUNDARY STRESS')
    print('=' * 80)

    # 1.1 Baseline Perfect Reading
    r_perfect = {
        'observed_at': datetime.now(timezone.utc),
        'pm1': 10.0,
        'pm2_5': 20.0,
        'pm10': 35.0,
        'temperature_c': 25.0,
        'humidity_pct': 55.0,
        'pressure_hpa': 1013.25,
        'wind_speed_m_s': 3.5,
        'wind_direction_deg': 180.0
    }
    res = QualityControlEngine.evaluate_reading(r_perfect)
    assert_test('1.1 Baseline Perfect Reading Score', res.quality_score == 1.0, f'Score={res.quality_score}')
    assert_test('1.1 Baseline Perfect Reading Status', res.quality_status == 'accepted', f'Status={res.quality_status}')
    assert_test('1.1 Baseline No Flags', not any([res.impossible_value_flag, res.high_humidity_flag, res.spike_review_flag, res.ordering_consistency_flag, res.timestamp_flag]))

    # 1.2 Boundary Condition: Negative PM2.5 (-10.0)
    r_neg = {
        'observed_at': datetime.now(timezone.utc),
        'pm2_5': -10.0,
        'temperature_c': 20.0
    }
    res_neg = QualityControlEngine.evaluate_reading(r_neg)
    assert_test('1.2 Negative PM2.5 (-10.0) Impossible Flag', res_neg.impossible_value_flag is True)
    assert_test('1.2 Negative PM2.5 (-10.0) Rejected Status', res_neg.quality_status == 'rejected', f'Status={res_neg.quality_status}')

    # 1.3 Boundary Condition: Negative PM2.5 (-0.01)
    r_neg_small = {
        'observed_at': datetime.now(timezone.utc),
        'pm2_5': -0.01,
        'temperature_c': 20.0
    }
    res_neg_small = QualityControlEngine.evaluate_reading(r_neg_small)
    assert_test('1.3 Small Negative PM2.5 (-0.01) Rejection', res_neg_small.impossible_value_flag is True and res_neg_small.quality_status == 'rejected')

    # 1.4 Boundary Condition: Valid Zero Floor (PM2.5 = 0.0)
    r_zero = {
        'observed_at': datetime.now(timezone.utc),
        'pm1': 0.0,
        'pm2_5': 0.0,
        'pm10': 0.0,
        'temperature_c': 0.0,
        'humidity_pct': 0.0,
        'pressure_hpa': 1000.0
    }
    res_zero = QualityControlEngine.evaluate_reading(r_zero)
    assert_test('1.4 Valid Zero Floor (0.0)', res_zero.impossible_value_flag is False and res_zero.quality_status == 'accepted', f'Score={res_zero.quality_score}')

    # 1.5 Particulate Ordering Violations: PM1 > PM2.5
    r_order1 = {
        'observed_at': datetime.now(timezone.utc) + timedelta(seconds=1),
        'pm1': 50.0,
        'pm2_5': 30.0,
        'pm10': 60.0
    }
    res_order1 = QualityControlEngine.evaluate_reading(r_order1)
    assert_test('1.5 Ordering Violation PM1 > PM2.5 Flag', res_order1.ordering_consistency_flag is True)
    assert_test('1.5 Ordering Violation PM1 > PM2.5 Score Penalty', res_order1.quality_score == 0.75, f'Score={res_order1.quality_score}')

    # 1.6 Particulate Ordering Violations: PM2.5 > PM10
    r_order2 = {
        'observed_at': datetime.now(timezone.utc) + timedelta(seconds=1),
        'pm1': 20.0,
        'pm2_5': 60.0,
        'pm10': 40.0
    }
    res_order2 = QualityControlEngine.evaluate_reading(r_order2)
    assert_test('1.6 Ordering Violation PM2.5 > PM10 Flag', res_order2.ordering_consistency_flag is True)
    assert_test('1.6 Ordering Violation PM2.5 > PM10 Score Penalty', res_order2.quality_score == 0.75, f'Score={res_order2.quality_score}')

    # 1.7 Particulate Ordering Violations: PM1 > PM2.5 > PM10 (Double Violation)
    r_order3 = {
        'observed_at': datetime.now(timezone.utc) + timedelta(seconds=1),
        'pm1': 80.0,
        'pm2_5': 60.0,
        'pm10': 40.0
    }
    res_order3 = QualityControlEngine.evaluate_reading(r_order3)
    assert_test('1.7 Double Ordering Violation (PM1 > PM2.5 > PM10)', res_order3.ordering_consistency_flag is True and res_order3.quality_score == 0.50, f'Score={res_order3.quality_score}')

    # 1.8 Particulate Ordering Equality: PM1 == PM2.5 == PM10 (Valid Physics Edge)
    r_order_eq = {
        'observed_at': datetime.now(timezone.utc),
        'pm1': 25.0,
        'pm2_5': 25.0,
        'pm10': 25.0
    }
    res_order_eq = QualityControlEngine.evaluate_reading(r_order_eq)
    assert_test('1.8 Particulate Ordering Equality (PM1=PM2.5=PM10)', res_order_eq.ordering_consistency_flag is False and res_order_eq.quality_score == 1.0)

    # 1.9 High Humidity Boundary: exactly 90.0% vs 90.1% vs 95.0%
    r_hum90 = {'observed_at': datetime.now(timezone.utc), 'pm2_5': 25.0, 'humidity_pct': 90.0}
    res_hum90 = QualityControlEngine.evaluate_reading(r_hum90)
    assert_test('1.9 Humidity exactly 90.0% (No Swelling Flag)', res_hum90.high_humidity_flag is False and res_hum90.quality_score == 1.0)

    r_hum901 = {'observed_at': datetime.now(timezone.utc), 'pm2_5': 25.0, 'humidity_pct': 90.1}
    res_hum901 = QualityControlEngine.evaluate_reading(r_hum901)
    assert_test('1.9 Humidity 90.1% (High Humidity Flag Triggered)', res_hum901.high_humidity_flag is True and res_hum901.quality_score == 0.85)

    r_hum95 = {'observed_at': datetime.now(timezone.utc), 'pm2_5': 25.0, 'humidity_pct': 95.0}
    res_hum95 = QualityControlEngine.evaluate_reading(r_hum95)
    assert_test('1.9 Humidity 95.0% (Warning State', res_hum95.high_humidity_flag is True and res_hum95.quality_status == 'accepted_with_warning')

    # 1.10 Extreme Humidity Out-of-Bounds (>100.0%)
    r_hum105 = {'observed_at': datetime.now(timezone.utc), 'humidity_pct': 105.0}
    res_hum105 = QualityControlEngine.evaluate_reading(r_hum105)
    assert_test('1.10 Impossible Humidity 105.0% Rejection', res_hum105.impossible_value_flag is True and res_hum105.quality_status == 'rejected')

    # 1.11 Extreme Particulate Spike (>150 ug/m3 delta)
    prev_reading = {'pm2_5': 30.0}
    curr_reading_spike = {'observed_at': datetime.now(timezone.utc), 'pm2_5': 185.0}
    res_spike = QualityControlEngine.evaluate_reading(curr_reading_spike, previous_reading=prev_reading)
    assert_test('1.11 Extreme Spike (Delta=155.0) Spike Flag', res_spike.spike_review_flag is True)
    assert_test('1.11 Extreme Spike (Delta=155.0) Score Penalty', res_spike.quality_score == 0.80, f'Score={res_spike.quality_score}')

    # 1.12 Non-Spike Boundary (Delta = 150.0 exactly)
    curr_reading_exact = {'observed_at': datetime.now(timezone.utc), 'pm2_5': 180.0}
    res_exact = QualityControlEngine.evaluate_reading(curr_reading_exact, previous_reading=prev_reading)
    assert_test('1.12 Delta exactly 150.0 (No Spike Flag)', res_exact.spike_review_flag is False and res_exact.quality_score == 1.0)

    # 1.13 Temperature Bounds (-20.0 to 60.0 C)
    assert_test('1.13 Temp Min Bound (-20.0 C)', QualityControlEngine.evaluate_reading( {'observed_at': datetime.now(timezone.utc), 'temperature_c': -20.0}).impossible_value_flag is False)
    assert_test('1.13 Temp Below Min (-21.0 C)', QualityControlEngine.evaluate_reading( {'observed_at': datetime.now(timezone.utc), 'temperature_c': -21.0}).impossible_value_flag is True)
    assert_test('1.13 Temp Max Bound (60.0 C)', QualityControlEngine.evaluate_reading( {'observed_at': datetime.now(timezone.utc), 'temperature_c': 60.0}).impossible_value_flag is False)
    assert_test('1.13 Temp Above Max (61.0 C)', QualityControlEngine.evaluate_reading( {'observed_at': datetime.now(timezone.utc), 'temperature_c': 61.0}).impossible_value_flag is True)

    # 1.14 Pressure Bounds (800.0 to 1100.0 hPa)
    assert_test('1.14 Pressure Min Bound (800.0 hPa)', QualityControlEngine.evaluate_reading( {'observed_at': datetime.now(timezone.utc), 'pressure_hpa': 800.0}).impossible_value_flag is False)
    assert_test('1.14 Pressure Below Min (799.0 hPa)', QualityControlEngine.evaluate_reading( {'observed_at': datetime.now(timezone.utc), 'pressure_hpa': 799.0}).impossible_value_flag is True)
    assert_test('1.14 Pressure Max Bound (1100.0 hPa)', QualityControlEngine.evaluate_reading( {'observed_at': datetime.now(timezone.utc), 'pressure_hpa': 1100.0}).impossible_value_flag is False)
    assert_test('1.14 Pressure Above Max (1101.0 hPa)', QualityControlEngine.evaluate_reading( {'observed_at': datetime.now(timezone.utc), 'pressure_hpa': 1101.0}).impossible_value_flag is True)

    # 1.15 Future Timestamp Detection
    future_ts = datetime.now(timezone.utc) + timedelta(hours=2)
    res_future = QualityControlEngine.evaluate_reading({'observed_at': future_ts, 'pm2_5': 25.0})
    assert_test('1.15 Future Timestamp Flag', res_future.timestamp_flag is True and res_future.quality_score == 0.70)

    # 1.16 Missing Timestamp Detection
    res_no_ts = QualityControlEngine.evaluate_reading({'pm2_5': 25.0})
    assert_test('1.16 Missing Timestamp Flag', res_no_ts.timestamp_flag is True and res_no_ts.quality_score == 0.50)

    # 1.17 Non-numeric values
    res_str = QualityControlEngine.evaluate_reading({'observed_at': datetime.now(timezone.utc), 'pm2_5': 'corrupted_string'})
    assert_test('1.17 Corrupted Non-Numeric Rejection', res_str.impossible_value_flag is True and res_str.quality_status == 'rejected')


    print('\n' + '=' * 80)
    print('CHALLENGE SUITE 2: CIRCULAR WND DIRECTION MATHEMATICAL EXACTNESS')
    print('=' * 80)

    # 2.1 Crossing 359 deg and 1 deg -> 0.0 deg (North)
    circ_359_1 = calculate_circular_wind_mean([359.0, 1.0])
    assert_test('2.1 Crossing 359 deg and 1 deg Mean = 0.0 deg', circ_359_1 == 0.0, f'Mean={circ_359_1}')

    # 2.2 Crossing 350 deg and 10 deg -> 0.0 deg (North)
    circ_350_10 = calculate_circular_wind_mean([350.0, 10.0])
    assert_test('2.2 Crossing 350 deg and 10 deg Mean = 0.0 deg', circ_350_10 == 0.0, f'Mean={circ_350_10}')

    # 2.3 East Quadrant: 89 deg and 91 deg -> 90.0 deg
    circ_89_91 = calculate_circular_wind_mean([89.0, 91.0])
    assert_test('2.3 East Quadrant [89, 91] Mean = 90.0 deg', circ_89_91 == 90.0, f'Mean={circ_89_91}')

    # 2.4 South Quadrant: 179 deg and 181 deg -> 180.0 deg
    circ_179_181 = calculate_circular_wind_mean([179.0, 181.0])
    assert_test('2.4 South Quadrant [179, 181] Mean = 180.0 deg', circ_179_181 == 180.0, f'Mean={circ_179_181}')

    # 2.5 West Quadrant: 269 deg and 271 deg -> 270.0 deg
    circ_269_271 = calculate_circular_wind_mean([269.0, 271.0])
    assert_test('2.5 West Quadrant [269, 271] Mean = 270.0 deg', circ_269_271 == 270.0, f'Mean={circ_269_271}')

    # 2.6 North-East Quadrant: 0 deg and 90 deg -> 45.0 deg
    circ_0_90 = calculate_circular_wind_mean([0.0, 90.0])
    assert_test('2.6 North-East [0, 90] Mean = 45.0 deg', circ_0_90 == 45.0, f'Mean={circ_0_90}')

    # 2.7 Opposite directions: 0 deg and 180 deg (Cancellation fallback)
    circ_opp = calculate_circular_wind_mean([0.0, 180.0])
    assert_test('2.7 Symmetrical Opposition [0, 180] Fallback to 0.0', circ_opp == 0.0, f'Mean={circ_opp}')

    # 2.8 Empty List & NaN Handling
    assert_test('2.8 Empty Degrees List returns None', calculate_circular_wind_mean([]) is None)
    assert_test('2.8 All None/NaN List returns None', calculate_circular_wind_mean([None, float("nan")]) is None)


    print('\n' + '=' * 80)
    print('CHALLENGE SUITE 3: INGESTION PIPELINE SCHEMAS & IDEMPOTENCY DEDUPLICATION')
    print('=' * 80)

    # 3.1 Content Hash Stability & Determinism
    t0 = datetime(2026, 8, 19, 14, 30, 0, tzinfo=timezone.utc)
    h1 = compute_content_hash('ISB-CAMPUS-01', t0, 25.5, 28.0)
    h2 = compute_content_hash('ISB-CAMPUS-01', t0, 25.5, 28.0)
    assert_test('3.1 Content Hash Determinism', h1 == h2 and len(h1) == 64, f'Hash={h1[:16]}...')

    # 3.2 Content Hash Sensitivity to slight perturbation
    h3 = compute_content_hash('ISB-CAMPUS-01', t0, 25.6, 28.0)
    assert_test('3.2 Content Hash Sensitivity (PM2.5 25.5 vs 25.6)', h1 != h3)

    # 3.3 ESP32 Ingest Payload Model Parsing (Canonical Format)
    canonical_dict = {
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
        'firmware_version': '1.0.0',
        'sequence_number': 1042
    }
    p_canon = ESP32IngestPayload(**canonical_dict)
    assert_test('3.3 Canonical Schema Validation', p_canon.pm2_5 == 14.2 and p_canon.sequence_number == 1042)

    # 3.4 ESP32 Ingest Payload Model Parsing (Nested Readings Legacy Format)
    legacy_dict = {
        'device_id': 'ESP32-ISB-01',
        'campus_code': 'ISB_CAMPUS',
        'timestamp_utc': '2026-08-19T14:30:00Z',
        'readings': {
            'pm1': 5.0,
            'pm25': 12.0,
            'pm10': 18.0,
            'temperature': 24.0,
            'humidity': 50.0,
            'pressure': 1010.0,
            'rain_flag': True
        }
    }
    p_legacy = ESP32IngestPayload(**legacy_dict)
    assert_test('3.4 Legacy Nested Readings Schema Validation', p_legacy.readings['pm25'] == 12.0 and p_legacy.readings['rain_flag'] is True)

    # 3.5 Token Generation and SHA-256 Salted Hashing
    raw_tok = generate_secure_token()
    tok_h = hash_token(raw_tok)
    assert_test('3.5 Secure Token Generation Length', len(raw_tok) >= 32)
    assert_test('3.5 Token Verification Positive', verify_token(raw_tok, tok_h) is True)
    assert_test('3.5 Token Verification Negative (Forged Token)', verify_token('forged_token_12345', tok_h) is False)


    print('\n' + '=' * 80)
    print('SUMMARY')
    print('=' * 80)
    print(f'Total Challenges Executed: {total}')
    print(f'Passed: {passed}')
    print(f'Failed: {failed}')
    print(f'Success Rate: {(passed / total) * 100:.1f}%')

    if failed == 0:
        print('\n^>>> ALL EMPIRICAL CHALLENGES PASSED! VERDICT: APPROVE <<<')
        return 0
    else:
        print(f'\n>>> {failed} CHALLENGES FAILED! VERDICT: CHALLENGE_FAILED <<<')
        return 1

if __name__ == '__main__':
    sys.exit(run_all_challenges())
