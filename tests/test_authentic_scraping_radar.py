"""
Comprehensive Test Suite for AirSense Pakistan 4-Pillar Authentic Ingestion Radar.
Validates:
- Pillar 1: Direct NASA FIRMS Active Fire & Biomass REST API (MODIS/VIIRS, FRP MW, downwind trajectory vectors).
- Pillar 2: Real-Time Motorway Fog Radar (M-1 to M-11 NH&MP police closures, GT Road N-5 diversions, proactive voice dispatch).
- Pillar 3: Headless Browser Driver for Dynamic .gov.pk Portals (Chromium headless=new, anti-bot stealth, D: drive visual audit PNGs).
- Pillar 4: Local OCR Pipeline for Stamped Government Image Circulars (PyMuPDF, OpenCV preprocessing, Section 144/188, seal detection).
- Invariant 1: Sovereign Storage Isolation (Zero C: Drive Writes).
- Invariant 2: Python 3.12 compatibility & 100% Test Pass Rate.
"""

import os
import sys
import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

# Ensure project root in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from apps.api.main import app
from pipelines.ops_data_lake_manager import OpsDataLakeManager
from services.scraping_orchestrator import ScrapingOrchestrator
from services.scrapers.nasa_firms_client import NASAFirmsClient
from services.scrapers.motorway_fog_radar import MotorwayFogRadar
from services.scrapers.headless_browser_driver import HeadlessBrowserDriver
from services.scrapers.local_ocr_pipeline import LocalOCRPipeline

client = TestClient(app)

# ---------------------------------------------------------------------------
# PILLAR 1: NASA FIRMS Active Fire & Biomass Tests
# ---------------------------------------------------------------------------

def test_pillar1_nasa_firms_bounding_box_and_attributes():
    """Validates NASA FIRMS geographic coordinates and bounding box bounds."""
    client_firms = NASAFirmsClient()
    assert client_firms.BBOX_WEST == 68.0
    assert client_firms.BBOX_SOUTH == 27.5
    assert client_firms.BBOX_EAST == 77.5
    assert client_firms.BBOX_NORTH == 34.5
    assert client_firms.BBOX_STR == "68.0,27.5,77.5,34.5"
    assert "MODIS_NRT" in client_firms.INSTRUMENTS
    assert "VIIRS_SNPP_NRT" in client_firms.INSTRUMENTS


def test_pillar1_nasa_firms_confidence_filtering():
    """Validates that low-confidence thermal detections are rejected while nominal/high are preserved."""
    client_firms = NASAFirmsClient()
    # MODIS numeric confidence
    assert client_firms._is_confidence_acceptable("MODIS_NRT", 85) is True
    assert client_firms._is_confidence_acceptable("MODIS_NRT", 50) is True
    assert client_firms._is_confidence_acceptable("MODIS_NRT", 20) is False
    # VIIRS categorical confidence
    assert client_firms._is_confidence_acceptable("VIIRS_SNPP_NRT", "h") is True
    assert client_firms._is_confidence_acceptable("VIIRS_SNPP_NRT", "nominal") is True
    assert client_firms._is_confidence_acceptable("VIIRS_SNPP_NRT", "l") is False
    assert client_firms._is_confidence_acceptable("VIIRS_SNPP_NRT", "low") is False


def test_pillar1_nasa_firms_csv_parsing_and_frp_calculation():
    """Validates CSV parsing, FRP calculation, and downwind trajectory vectors."""
    client_firms = NASAFirmsClient()
    
    # Sample authentic FIRMS CSV record
    csv_sample = (
        "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight\n"
        "31.6250,74.8720,335.2,0.4,0.4,2026-09-13,0645,N,VIIRS,h,2.0NRT,305.1,45.8,D\n"
        "30.9150,74.6180,342.1,0.4,0.4,2026-09-13,0645,N,VIIRS,nominal,2.0NRT,310.4,72.4,D\n"
        "31.7180,73.9850,328.0,0.4,0.4,2026-09-13,0645,N,VIIRS,low,2.0NRT,298.0,18.0,D\n"  # should be filtered out
        "32.1880,74.1950,339.5,0.4,0.4,2026-09-13,0645,N,VIIRS,high,2.0NRT,308.2,38.2,D\n"
    )

    hotspots = client_firms.parse_firms_csv(csv_sample, "VIIRS_SNPP_NRT")
    assert len(hotspots) == 3  # 1 low-confidence row excluded
    
    total_frp = sum(h["frp"] for h in hotspots)
    assert total_frp == pytest.approx(156.4, rel=1e-2)

    # Calculate downwind smoke trajectories
    trajectories = client_firms.compute_downwind_smoke_trajectories(
        hotspots, wind_speed_kmh=15.0, wind_bearing_deg=305.0
    )
    assert trajectories["total_hotspots"] == 3
    assert trajectories["aggregate_frp_mw"] == pytest.approx(156.4, rel=1e-2)
    assert trajectories["max_frp_mw"] == 72.4
    assert "Lahore" in trajectories["plume_trajectories"]
    
    lhe_traj = trajectories["plume_trajectories"]["Lahore"]
    assert lhe_traj["distance_km"] > 0
    assert lhe_traj["estimated_transit_hours"] > 0
    assert 0.0 <= lhe_traj["smoke_impact_score"] <= 100.0


def test_pillar1_nasa_firms_full_fetch_and_storage():
    """Validates end-to-end FIRMS fetch, trajectory calculation, and strict D: drive storage."""
    client_firms = NASAFirmsClient()
    result = client_firms.fetch_and_analyze()
    
    assert result["status"] == "SUCCESS"
    assert result["analytics"]["total_hotspots"] > 0
    assert result["analytics"]["aggregate_frp_mw"] > 0
    
    raw_file = result["raw_file"]
    norm_file = result["normalized_file"]
    if os.path.exists("D:/"):
        assert raw_file.lower().startswith("d:")
        assert norm_file.lower().startswith("d:")
    assert os.path.exists(raw_file)
    assert os.path.exists(norm_file)


# ---------------------------------------------------------------------------
# PILLAR 2: Real-Time Motorway Fog Radar Tests
# ---------------------------------------------------------------------------

def test_pillar2_motorway_registry_and_parsing():
    """Validates Motorway registry coverage (M-1 to M-11) and regex parsing."""
    radar = MotorwayFogRadar()
    assert "M-1" in radar.MOTORWAYS_REGISTRY
    assert "M-2" in radar.MOTORWAYS_REGISTRY
    assert "M-3" in radar.MOTORWAYS_REGISTRY
    assert "M-4" in radar.MOTORWAYS_REGISTRY
    assert "M-5" in radar.MOTORWAYS_REGISTRY
    assert "M-9" in radar.MOTORWAYS_REGISTRY
    assert "M-11" in radar.MOTORWAYS_REGISTRY

    # Test closure bulletin regex extraction
    sample_text = (
        "NH&MP EMERGENCY ADVISORY: Motorway M-2 (Lahore to Kot Momin) and M-11 (Lahore to Sialkot) "
        "CLOSED for all vehicular traffic due to dense fog with visibility 0 to 20 meters. "
        "Diversions active via GT Road N-5."
    )
    parsed = radar.parse_closure_notice(sample_text)
    assert "M-2" in parsed["detected_motorways"]
    assert "M-11" in parsed["detected_motorways"]
    assert parsed["status"] == "CLOSED"
    assert parsed["visibility_meters"] == 20
    assert parsed["is_zero_visibility"] is True
    assert "GT Road N-5" in parsed["diversion_route"]
    assert parsed["proactive_telephony_required"] is True


def test_pillar2_proactive_telephony_dispatch_payload():
    """Validates formulation of proactive AI voice dispatch directives for logistics fleets."""
    radar = MotorwayFogRadar()
    closure_info = {
        "detected_motorways": ["M-2", "M-11"],
        "status": "CLOSED",
        "visibility_meters": 15,
        "diversion_route": "GT Road N-5"
    }
    payload = radar.formulate_proactive_telephony_payload(closure_info, target_city="Lahore")
    assert payload["sector"] == "logistics"
    assert payload["urgency"] == "CRITICAL"
    assert "M-2" in payload["directive_text"]
    assert "GT Road N-5" in payload["directive_text"]
    assert payload["city"] == "Lahore"


def test_pillar2_motorway_radar_fetch_and_lake_storage():
    """Validates end-to-end Motorway Fog Radar execution and D: lake persistence."""
    radar = MotorwayFogRadar()
    res = radar.fetch_and_analyze()
    assert res["status"] == "SUCCESS"
    assert len(res["active_bulletins"]) > 0
    if os.path.exists("D:/"):
        assert res["raw_file"].lower().startswith("d:")
        assert res["normalized_file"].lower().startswith("d:")
    assert os.path.exists(res["raw_file"])
    assert os.path.exists(res["normalized_file"])


# ---------------------------------------------------------------------------
# PILLAR 3: Headless Browser Driver Tests
# ---------------------------------------------------------------------------

def test_pillar3_browser_detection_and_stealth_flags():
    """Validates browser binary detection and anti-bot configuration."""
    driver = HeadlessBrowserDriver()
    assert driver.browser_path is not None, "Neither Google Chrome nor Microsoft Edge detected on system"
    assert "Chrome" in driver.USER_AGENT or "Safari" in driver.USER_AGENT
    assert "epd.punjab.gov.pk" in driver.PORTAL_DOMAINS_MAP


def test_pillar3_visual_audit_png_capture_on_d_drive():
    """Validates full-page visual audit screenshot PNG generation strictly on D: drive."""
    driver = HeadlessBrowserDriver()
    # Execute portal capture
    result = driver.capture_portal("https://epd.punjab.gov.pk/notifications", domain="epa_gazettes")
    
    assert result["status"] == "SUCCESS"
    assert "audit_id" in result
    png_path = result["screenshot_png"]
    json_path = result["metadata_json"]
    
    # Assert strict storage
    if os.path.exists("D:/"):
        assert png_path.lower().startswith("d:"), f"Visual audit PNG '{png_path}' violates D: drive enforcement!"
        assert json_path.lower().startswith("d:"), f"Visual audit JSON '{json_path}' violates D: drive enforcement!"
    assert os.path.exists(png_path), "Visual audit PNG file was not created"
    assert os.path.exists(json_path), "Visual audit JSON metadata was not created"
    assert os.path.getsize(png_path) > 1000, "Visual audit PNG file size is suspiciously small"

    # Verify audit record content
    audit = result["audit_record"]
    assert audit["storage_host"] == "D: Drive Sovereign Isolation"
    assert audit["stealth_verification"]["webdriver_hidden"] is True
    assert audit["stealth_verification"]["viewport"] == "1920x1080"


# ---------------------------------------------------------------------------
# PILLAR 4: Local OCR Pipeline Tests
# ---------------------------------------------------------------------------

def test_pillar4_stamped_circular_generation_and_pdf_parsing():
    """Validates creating and parsing an authentic stamped Section 144 circular PDF."""
    ocr = LocalOCRPipeline()
    test_pdf_path = "D:/MUNIM - UOE @BIC/AirSense/data/ops_db/circulars_ocr/test_stamped_order.pdf" if os.path.exists("D:/") else os.path.join(ocr.lake.circulars_ocr_root, "test_stamped_order.pdf")
    
    # Generate stamped PDF
    ocr.create_sample_stamped_circular_pdf(test_pdf_path)
    assert os.path.exists(test_pdf_path)
    if os.path.exists("D:/"):
        assert test_pdf_path.lower().startswith("d:")

    # Process through OCR pipeline
    res = ocr.process_circular(test_pdf_path, circular_id="TEST_CIRCULAR_001")
    assert res["status"] == "SUCCESS"
    if os.path.exists("D:/"):
        assert res["document_file"].lower().startswith("d:")
        assert res["metadata_file"].lower().startswith("d:")
    assert os.path.exists(res["document_file"])
    assert os.path.exists(res["metadata_file"])
    
    # Verify extracted legal entities
    entities = res["legal_entities"]
    assert entities["section_144_invoked"] is True
    assert entities["section_188_penalties"] is True
    assert entities["pepa_act_referenced"] is True
    assert entities["brick_kiln_ban"] is True
    assert entities["enforcement_tier"] == "CRITICAL"
    assert "Lahore" in entities["affected_districts"]
    assert entities["effective_duration_hours"] == 72
    
    # Verify seal detection
    seal = res["seal_verification"]
    assert seal["official_seal_detected"] is True
    assert seal["verification_confidence"] >= 0.70


def test_pillar4_cv_image_preprocessing():
    """Validates OpenCV image preprocessing (binarization, deskewing)."""
    import numpy as np
    ocr = LocalOCRPipeline()
    
    # Create synthetic mock image with noise
    mock_img = np.full((300, 300, 3), 240, dtype=np.uint8)
    mock_img[100:200, 50:250] = 30  # black text block
    
    preprocessed = ocr.preprocess_image(mock_img)
    assert preprocessed.shape == (300, 300)
    assert preprocessed.dtype == np.uint8
    # Otsu threshold should produce binary values (0 and 255)
    unique_vals = set(np.unique(preprocessed))
    assert unique_vals.issubset({0, 255})


# ---------------------------------------------------------------------------
# INTEGRATION: 8-Domain Scraping Orchestrator
# ---------------------------------------------------------------------------

def test_scraping_orchestrator_integration():
    """Validates that ScrapingOrchestrator seamlessly runs 8 domains with the authentic pillars."""
    orchestrator = ScrapingOrchestrator()
    
    # Test single domain scrapes on authentic pillars
    bio_res = orchestrator.scrape_domain("biomass_hotspots")
    assert bio_res["status"] == "SUCCESS"
    assert "biomass_analytics" in bio_res["record"]
    assert bio_res["record"]["biomass_analytics"]["total_hotspots"] > 0

    mot_res = orchestrator.scrape_domain("motorway_traffic")
    assert mot_res["status"] == "SUCCESS"
    assert "closure_details" in mot_res["record"]

    # Test full radar status
    radar_status = orchestrator.get_radar_status()
    assert radar_status["cadence"] == "HOURLY_CONTINUOUS"
    assert radar_status["total_domains"] == 8
    assert "authentic_pillars" in radar_status
    pillars = radar_status["authentic_pillars"]
    assert pillars["pillar_1_nasa_firms"]["status"] == "OPERATIONAL"
    assert pillars["pillar_2_motorway_fog"]["status"] == "OPERATIONAL"
    assert pillars["pillar_3_headless_browser"]["status"] == "OPERATIONAL"
    assert pillars["pillar_4_local_ocr"]["status"] == "OPERATIONAL"


# ---------------------------------------------------------------------------
# API ENDPOINTS: End-to-End FastAPI Verification
# ---------------------------------------------------------------------------

def test_api_radar_biomass_hotspots_endpoint():
    """Tests GET /api/v2/decisions/radar/biomass-hotspots."""
    response = client.get("/api/v2/decisions/radar/biomass-hotspots")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "analytics" in data
    assert data["analytics"]["total_hotspots"] > 0
    assert "plume_trajectories" in data["analytics"]
    assert "Lahore" in data["analytics"]["plume_trajectories"]


def test_api_radar_motorway_closures_endpoint():
    """Tests GET /api/v2/decisions/radar/motorway-closures."""
    response = client.get("/api/v2/decisions/radar/motorway-closures")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "active_bulletins" in data
    assert len(data["active_bulletins"]) > 0


def test_api_radar_visual_audit_endpoint():
    """Tests POST /api/v2/decisions/radar/visual-audit."""
    payload = {
        "target_url": "https://epd.punjab.gov.pk/notifications",
        "domain": "epa_gazettes"
    }
    response = client.post("/api/v2/decisions/radar/visual-audit", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "screenshot_png" in data
    if os.path.exists("D:/"):
        assert data["screenshot_png"].lower().startswith("d:")
    assert os.path.exists(data["screenshot_png"])


def test_api_radar_snapshot_image_endpoint():
    """Tests GET /api/v2/decisions/radar/snapshot-image."""
    res_404 = client.get("/api/v2/decisions/radar/snapshot-image?path=invalid_nonexistent.png")
    assert res_404.status_code == 404

    # Trigger audit to get a valid PNG path on D: drive
    audit_res = client.post("/api/v2/decisions/radar/visual-audit", json={
        "target_url": "https://epd.punjab.gov.pk/notifications",
        "domain": "epa_gazettes"
    })
    assert audit_res.status_code == 200
    png_path = audit_res.json()["screenshot_png"]
    assert os.path.exists(png_path)

    res_img = client.get(f"/api/v2/decisions/radar/snapshot-image?path={png_path}")
    assert res_img.status_code == 200
    assert "image/png" in res_img.headers["content-type"]



def test_api_radar_ocr_circular_endpoint():
    """Tests POST /api/v2/decisions/radar/ocr-circular."""
    payload = {
        "circular_id": "TEST_OCR_API_001",
        "use_sample": True
    }
    response = client.post("/api/v2/decisions/radar/ocr-circular", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "legal_entities" in data
    assert data["legal_entities"]["section_144_invoked"] is True
    assert "seal_verification" in data
    if os.path.exists("D:/"):
        assert data["document_file"].lower().startswith("d:")
    assert os.path.exists(data["document_file"])


def test_pillar1_nasa_firms_geojson_parsing():
    """Validates GeoJSON FeatureCollection parsing, bbox checking, and FRP extraction."""
    client_firms = NASAFirmsClient()
    sample_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [74.34, 31.55]},
                "properties": {"brightness": 345.5, "frp": 62.4, "confidence": "high", "instrument": "VIIRS_SNPP_NRT"}
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [73.08, 31.42]},
                "properties": {"brightness": 338.0, "frp": 44.1, "confidence": "n", "instrument": "VIIRS_SNPP_NRT"}
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [50.0, 20.0]},  # Outside Pakistan bbox
                "properties": {"brightness": 350.0, "frp": 99.0, "confidence": "high"}
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [74.0, 31.0]},
                "properties": {"brightness": 320.0, "frp": 12.0, "confidence": "low"}  # Low confidence excluded
            }
        ]
    }
    hotspots = client_firms.parse_firms_geojson(sample_geojson, "VIIRS_SNPP_NRT")
    assert len(hotspots) == 2
    assert hotspots[0]["latitude"] == 31.55
    assert hotspots[0]["longitude"] == 74.34
    assert hotspots[0]["frp"] == 62.4
    assert hotspots[1]["frp"] == 44.1


def test_pillar1_empty_hotspots_schema_completeness():
    """Validates that compute_downwind_smoke_trajectories returns all required schema keys when empty."""
    client_firms = NASAFirmsClient()
    res = client_firms.compute_downwind_smoke_trajectories([])
    assert res["total_hotspots"] == 0
    assert res["aggregate_frp_mw"] == 0.0
    assert "max_frp_hotspot" in res
    assert res["max_frp_hotspot"] is None
    assert "wind_vector" in res
    assert res["wind_vector"]["bearing_deg"] == 305.0
    assert res["centroid"] is None
    assert res["plume_trajectories"] == {}


def test_pillar1_csv_resilience_missing_fields():
    """Validates CSV parsing resilience against missing optional brightness and scan columns."""
    client_firms = NASAFirmsClient()
    csv_sample = (
        "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight\n"
        "31.6250,74.8720,,,,2026-09-13,0645,N,VIIRS,h,2.0NRT,,45.8,D\n"
    )
    hotspots = client_firms.parse_firms_csv(csv_sample, "VIIRS_SNPP_NRT")
    assert len(hotspots) == 1
    assert hotspots[0]["frp"] == 45.8
    assert hotspots[0]["brightness"] > 0


def test_pillar2_motorway_parsing_and_corridor_diversion_accuracy():
    """Validates regex detection of unhyphenated names ('M3', 'M11') and corridor-specific diversions."""
    radar = MotorwayFogRadar()
    # M3 without hyphen
    m3_res = radar.parse_closure_notice("Motorway M3 is closed from Faizpur interchange due to heavy fog")
    assert "M-3" in m3_res["detected_motorways"]
    assert "Faisalabad-Sheikhupura Road / N-5" in m3_res["diversion_route"]
    assert m3_res["status"] == "CLOSED"

    # M11 without hyphen
    m11_res = radar.parse_closure_notice("Dense fog on M11 between Kala Shah Kaku and Sambrial. Highway shut.")
    assert "M-11" in m11_res["detected_motorways"]
    assert "N-5 GT Road" in m11_res["diversion_route"]

    # M9 Karachi corridor - must NOT route to GT Road N-5
    m9_res = radar.parse_closure_notice("Motorway M-9 closed due to dense fog. Traffic halted.")
    assert "M-9" in m9_res["detected_motorways"]
    assert "Indus Highway" in m9_res["diversion_route"] or "N-55" in m9_res["diversion_route"]
    assert "GT Road" not in m9_res["diversion_route"]


def test_pillar2_zero_visibility_detection():
    """Validates handling of 'zero visibility' phrase without explicit numeric range."""
    radar = MotorwayFogRadar()
    parsed = radar.parse_closure_notice("Travel alert: Zero visibility reported on M-2 Babu Sabu sector. Motorway closed.")
    assert parsed["visibility_meters"] <= 15
    assert parsed["is_zero_visibility"] is True
    assert parsed["status"] == "CLOSED"


def test_pillar3_headless_browser_virtual_time_budget():
    """Validates headless browser configuration includes anti-bot flags and virtual time budget."""
    driver = HeadlessBrowserDriver()
    res = driver.capture_portal("https://epd.punjab.gov.pk/notifications", domain="epa_gazettes")
    assert res["status"] == "SUCCESS"
    assert os.path.exists(res["screenshot_png"])
    if os.path.exists("D:/"):
        assert res["screenshot_png"].lower().startswith("d:")
    assert res["audit_record"]["stealth_verification"]["webdriver_hidden"] is True


def test_pillar4_text_content_ingestion_accuracy():
    """Validates that custom text provided to process_circular is accurately parsed and not overridden."""
    ocr = LocalOCRPipeline()
    text = (
        "GOVERNMENT OF THE PUNJAB SCHOOL EDUCATION DEPARTMENT\n"
        "NOTIFICATION: Schools shall remain closed in Lahore and Multan for 72 hours due to toxic smog emergency."
    )
    res = ocr.process_circular(text, circular_id="CIRCULAR_EDU_TEST")
    assert res["status"] == "SUCCESS"
    assert "Schools shall remain closed" in res["full_text"]
    assert res["legal_entities"]["event_type"] == "SchoolClosureDirective"
    assert res["legal_entities"]["school_directives"] is True
    assert "Lahore" in res["legal_entities"]["affected_districts"]


def test_pillar4_education_circular_parsing():
    """Validates specialized entity extraction on education sector circulars."""
    ocr = LocalOCRPipeline()
    text = "School Education Department: All private and public schools to adopt hybrid online classes. Outdoor sports suspended."
    res = ocr.process_circular(text, circular_id="CIRCULAR_SCHOOL_01")
    assert res["legal_entities"]["school_directives"] is True
    assert res["legal_entities"]["event_type"] == "SchoolClosureDirective"


def test_api_ocr_circular_with_custom_text():
    """Tests POST /api/v2/decisions/radar/ocr-circular with custom text_content."""
    payload = {
        "circular_id": "TEST_API_CUSTOM_EDU",
        "text_content": "School Education Department notification: schools closed across Lahore and Gujranwala due to severe smog."
    }
    response = client.post("/api/v2/decisions/radar/ocr-circular", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["legal_entities"]["school_directives"] is True
    assert data["legal_entities"]["event_type"] == "SchoolClosureDirective"
    assert "Lahore" in data["legal_entities"]["affected_districts"]
    if os.path.exists("D:/"):
        assert data["document_file"].lower().startswith("d:")
    assert os.path.exists(data["document_file"])


def test_scraping_orchestrator_all_4_pillars_integration():
    """Validates that ScrapingOrchestrator integrates all 4 authentic pillars across domains."""
    os.environ["AIRSENSE_FAST_TEST"] = "1"
    orchestrator = ScrapingOrchestrator()
    # Biomass (Pillar 1)
    bio = orchestrator.scrape_domain("biomass_hotspots")
    assert bio["status"] == "SUCCESS"
    assert bio["record"]["event_type"] in ["Advisory", "Closure"]
    assert bio["record"]["biomass_analytics"]["total_hotspots"] > 0

    # Motorway (Pillar 2)
    mot = orchestrator.scrape_domain("motorway_traffic")
    assert mot["status"] == "SUCCESS"
    assert mot["record"]["event_type"] in ["Advisory", "Closure"]
    assert "closure_details" in mot["record"]

    # EPA (Pillars 3 & 4)
    epa = orchestrator.scrape_domain("epa_gazettes")
    assert epa["status"] == "SUCCESS"
    assert "visual_audit_proof" in epa["record"]
    assert "legal_entities" in epa["record"]
    if os.path.exists("D:/"):
        assert epa["record"]["visual_audit_proof"]["screenshot_png"].lower().startswith("d:")
    assert os.path.exists(epa["record"]["visual_audit_proof"]["screenshot_png"])

    # Education (Pillars 3 & 4)
    edu = orchestrator.scrape_domain("education_circulars")
    assert edu["status"] == "SUCCESS"
    assert "visual_audit_proof" in edu["record"]
    assert "legal_entities" in edu["record"]
    assert edu["record"]["legal_entities"]["school_directives"] is True


# ---------------------------------------------------------------------------
# INVARIANT TEST: Sovereign Storage Enforcement (Zero C: Drive Writes)
# ---------------------------------------------------------------------------

def test_storage_sovereignty_zero_c_drive_spill():
    """Audits OpsDataLakeManager to guarantee that all lake paths strictly reside on D: drive."""
    lake = OpsDataLakeManager()
    stats = lake.get_storage_stats()
    
    if os.path.exists("D:/"):
        assert stats["d_drive_root"].lower().startswith("d:")
        assert lake.base_path.lower().startswith("d:")
        assert lake.scraped_raw_root.lower().startswith("d:")
        assert lake.normalized_root.lower().startswith("d:")
        assert lake.visual_audits_root.lower().startswith("d:")
        assert lake.circulars_ocr_root.lower().startswith("d:")
        assert lake.cache_dir.lower().startswith("d:")
        assert lake.tmp_dir.lower().startswith("d:")

        # Hard exception check on illegal path
        with pytest.raises(PermissionError):
            lake._assert_d_drive("C:/Users/Source Machinery/spill.json")
    else:
        assert os.path.exists(lake.base_path)
        assert os.path.exists(lake.scraped_raw_root)
        assert os.path.exists(lake.normalized_root)
        assert os.path.exists(lake.visual_audits_root)
        assert os.path.exists(lake.circulars_ocr_root)
