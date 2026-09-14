import os
import time
import pytest
from unittest.mock import MagicMock
import requests

from services.scraping_orchestrator import ScrapingOrchestrator

@pytest.fixture
def orchestrator():
    os.environ["AIRSENSE_FAST_TEST"] = "1"
    return ScrapingOrchestrator()

def test_scrape_domain_produces_valid_normalized_schema(orchestrator):
    """Verify scrape_domain produces valid normalized schemas across domains."""
    for domain in orchestrator.DOMAINS_METADATA:
        res = orchestrator.scrape_domain(domain)
        assert res["status"] == "SUCCESS", f"Domain {domain} failed to scrape"
        assert os.path.exists(res["raw_file"]), f"Raw file '{res['raw_file']}' not found"
        assert os.path.exists(res["normalized_file"]), f"Normalized file '{res['normalized_file']}' not found"
        
        record = res["record"]
        assert record["domain"] == domain
        assert "event_id" in record
        assert "source_url" in record
        assert "timestamp" in record
        assert "iso_timestamp" in record
        assert "raw_text" in record and len(record["raw_text"]) > 0
        assert "event_type" in record and record["event_type"] in ["Advisory", "Closure"]
        assert "affected_sectors" in record and isinstance(record["affected_sectors"], list)
        assert "extracted_lead_time_hours" in record and record["extracted_lead_time_hours"] > 0
        assert "urgency_tier" in record and record["urgency_tier"] in ["CRITICAL", "ELEVATED"]
        assert "enforcement_action" in record and record["enforcement_action"] in ["ENFORCED", "MONITORED"]

def test_run_hourly_cycle_sweeps_all_8_domains(orchestrator):
    """Verify run_hourly_cycle() concurrently sweeps all 8 domains using ThreadPoolExecutor."""
    result = orchestrator.run_hourly_cycle()
    assert result["cycle_status"] == "COMPLETED"
    assert result["domains_scraped"] == 8
    assert "duration_seconds" in result
    assert result["duration_seconds"] > 0
    
    for domain in orchestrator.DOMAINS_METADATA:
        assert domain in result["results"], f"Domain '{domain}' missing from cycle results"
        domain_res = result["results"][domain]
        assert domain_res["status"] == "SUCCESS"
        assert "raw_file" in domain_res
        assert "normalized_file" in domain_res

def test_get_radar_status_returns_8_healthy_domains(orchestrator):
    """Verify get_radar_status() returns 8 operational domains with status == 'HEALTHY'."""
    radar_data = orchestrator.get_radar_status()
    assert radar_data["cadence"] == "HOURLY_CONTINUOUS"
    assert radar_data["total_domains"] == 8
    assert len(radar_data["radar"]) == 8
    
    domain_keys = [item["domain_key"] for item in radar_data["radar"]]
    expected_domains = list(orchestrator.DOMAINS_METADATA.keys())
    assert sorted(domain_keys) == sorted(expected_domains)
    
    for item in radar_data["radar"]:
        assert item["status"] == "HEALTHY", f"Domain {item['domain_key']} status is {item['status']}"
        assert item["health_pct"] >= 90.0
        assert item["target_endpoints"] > 0
        assert item["indexed_notices_count"] >= 0
        assert "last_sync" in item

def test_live_http_request_mock_success(monkeypatch, orchestrator):
    """Verify live HTTP request is properly formatted with headers and handles successful response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "NOTAM: Visibility at Lahore Airport reduced to 50 meters due to severe fog."
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_resp)
    
    payload = orchestrator._fetch_live_payload("aviation_transport", "https://caapakistan.com.pk/notams")
    assert payload is not None
    assert payload["is_live"] is True
    assert payload["http_status"] == 200
    assert "Visibility at Lahore Airport" in payload["raw_text"]

def test_live_http_fallback_on_network_failure(monkeypatch, orchestrator):
    """Verify immediate graceful fallback to synthetic payload on network connection failure."""
    def mock_fail(*args, **kwargs):
        raise requests.exceptions.ConnectionError("Connection refused by remote host")
    
    monkeypatch.setattr(requests, "get", mock_fail)
    
    # Live fetch should immediately return None without raising
    payload = orchestrator._fetch_live_payload("power_grid", "https://ntdc.com.pk/grid")
    assert payload is None
    
    # scrape_domain should gracefully fall back to synthetic notice
    res = orchestrator.scrape_domain("power_grid")
    assert res["status"] == "SUCCESS"
    assert "raw_file" in res

def test_exponential_backoff_retry_on_server_error(monkeypatch, orchestrator):
    """Verify exponential backoff retry on transient 5xx server errors."""
    call_count = [0]
    
    def mock_retry(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] < 2:
            resp_500 = MagicMock()
            resp_500.status_code = 503
            return resp_500
        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.text = "LCCI: Supply chain routes re-opened after smog clearance."
        return resp_200
        
    monkeypatch.setattr(requests, "get", mock_retry)
    
    payload = orchestrator._fetch_live_payload("industrial_chambers", "https://lcci.com.pk")
    assert payload is not None
    assert call_count[0] >= 2
    assert "Supply chain routes" in payload["raw_text"]

def test_unknown_domain_raises_value_error(orchestrator):
    """Verify unknown domain raises ValueError."""
    with pytest.raises(ValueError):
        orchestrator.scrape_domain("unregistered_domain_123")
