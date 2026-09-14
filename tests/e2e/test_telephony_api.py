import json
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)

def test_telephony_status_endpoint():
    response = client.get("/api/v2/telephony/status")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "allocated_numbers" in data
    assert "configured_ai_agents" in data
    assert "supported_languages" in data
    assert "ur" in data["supported_languages"]

def test_telephony_dispatch_call_endpoint():
    payload = {
        "to_number": "+923001234567",
        "recipient_name": "Hamid Raza (Logistics Dir)",
        "sector": "logistics",
        "urgency": "HIGH",
        "predicted_day": 3,
        "pm2_5_projected": 395.0,
        "city": "Lahore"
    }
    response = client.post("/api/v2/telephony/dispatch-call", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DISPATCHED"
    assert data["record"]["type"] == "VOICE_CALL"
    assert data["record"]["status"] == "COMPLETED"

def test_telephony_dispatch_sms_endpoint():
    payload = {
        "to_number": "+923001234567",
        "recipient_name": "Campus Lead",
        "sector": "education",
        "city": "Lahore",
        "day_horizon": 2,
        "mitigation_savings_pkr": 2500000.0
    }
    response = client.post("/api/v2/telephony/dispatch-sms", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DISPATCHED"
    assert data["record"]["type"] == "SMS_ALERT"

def test_telephony_history_endpoint():
    response = client.get("/api/v2/telephony/history?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert isinstance(data["history"], list)

def test_telephony_dispatch_call_bilingual_urdu():
    payload = {
        "to_number": "+923001234567",
        "recipient_name": "حمید رضا",
        "sector": "logistics",
        "urgency": "CRITICAL",
        "predicted_day": 3,
        "pm2_5_projected": 420.0,
        "city": "Lahore",
        "language": "ur"
    }
    response = client.post("/api/v2/telephony/dispatch-call", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DISPATCHED"
    record = data["record"]
    assert record["type"] == "VOICE_CALL"
    assert record["language"] == "ur"
    assert record["status"] == "COMPLETED"
    assert len(record["turns"]) >= 4
    # Assert Urdu script is spoken by the agent
    assert any("السلام علیکم" in turn["text"] or "موٹروے" in turn["text"] for turn in record["turns"])

def test_telephony_dispatch_sms_bilingual_urdu():
    payload = {
        "to_number": "+923009876543",
        "recipient_name": "پرنسپل عائشہ",
        "sector": "education",
        "city": "Lahore",
        "day_horizon": 2,
        "mitigation_savings_pkr": 2800000.0,
        "language": "ur"
    }
    response = client.post("/api/v2/telephony/dispatch-sms", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DISPATCHED"
    record = data["record"]
    assert record["type"] == "SMS_ALERT"
    assert record["language"] == "ur"
    assert "ایئر سینس" in record["body"] or "اسموگ" in record["body"]

def test_telephony_webhook_sms_ack():
    payload = {
        "channel": "sms",
        "from": "+923001234567",
        "text": "Alert acknowledged. Fleet rerouting initiated."
    }
    response = client.post("/api/v2/telephony/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "acknowledged"

def test_telephony_webhook_voice_streaming_ndjson():
    payload = {
        "channel": "voice",
        "callId": "call_stream_test_01",
        "sector": "logistics",
        "language": "en",
        "data": {
            "transcript": "What is the motorway visibility tonight on M-2?"
        }
    }
    response = client.post("/api/v2/telephony/webhook", json=payload)
    assert response.status_code == 200
    assert "application/x-ndjson" in response.headers.get("content-type", "")
    lines = [json.loads(line) for line in response.text.strip().split("\n") if line.strip()]
    assert len(lines) == 2
    # Chunk 1: Interim sub-second response
    assert lines[0]["interim"] is True
    assert "text" in lines[0]
    assert len(lines[0]["text"]) > 0
    # Chunk 2: Final response
    assert lines[1]["interim"] is False
    assert "Motorway" in lines[1]["text"] or "GT Road" in lines[1]["text"]

def test_telephony_webhook_voice_streaming_urdu():
    payload = {
        "channel": "voice",
        "callId": "call_stream_test_02",
        "sector": "education",
        "language": "ur",
        "data": {
            "transcript": "اسکولوں کے اوقات کار میں کیا تبدیلی ہوگی؟"
        }
    }
    response = client.post("/api/v2/telephony/webhook", json=payload)
    assert response.status_code == 200
    assert "application/x-ndjson" in response.headers.get("content-type", "")
    lines = [json.loads(line) for line in response.text.strip().split("\n") if line.strip()]
    assert len(lines) == 2
    # Chunk 1: Interim Urdu
    assert lines[0]["interim"] is True
    assert "انتظار" in lines[0]["text"] or "ایئر سینس" in lines[0]["text"]
    # Chunk 2: Final Urdu
    assert lines[1]["interim"] is False
    assert "اسکول" in lines[1]["text"] or "فضائی" in lines[1]["text"]

