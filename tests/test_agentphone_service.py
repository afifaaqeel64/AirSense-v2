import pytest
import os
from services.telephony.agentphone_service import AgentPhoneService

@pytest.mark.asyncio
async def test_agentphone_status():
    service = AgentPhoneService()
    status = service.get_status()
    assert "service" in status
    assert "allocated_numbers" in status
    assert len(status["allocated_numbers"]) >= 2
    assert "configured_ai_agents" in status
    assert len(status["configured_ai_agents"]) >= 4

@pytest.mark.asyncio
async def test_agentphone_voice_call_dispatch():
    service = AgentPhoneService()
    record = await service.dispatch_voice_call(
        to_number="+923001234567",
        recipient_name="Tariq Mansoor (Logistics Dir)",
        sector="logistics",
        predicted_day=3,
        pm2_5_projected=410.0,
        city="Lahore"
    )
    assert record["status"] == "COMPLETED"
    assert record["type"] == "VOICE_CALL"
    assert len(record["turns"]) >= 4
    assert "Logistics" in record["voice_agent"]

@pytest.mark.asyncio
async def test_agentphone_sms_dispatch():
    service = AgentPhoneService()
    record = await service.dispatch_emergency_sms(
        to_number="+923007654321",
        recipient_name="Principal Ayesha (Campus Lead)",
        sector="education",
        city="Lahore",
        day_horizon=3,
        mitigation_savings_pkr=1450000.0
    )
    assert record["status"] == "DELIVERED"
    assert record["type"] == "SMS_ALERT"
    assert "AIRSENSE ALERT" in record["body"]

@pytest.mark.asyncio
async def test_agentphone_dispatch_history():
    service = AgentPhoneService()
    history = service.get_dispatch_history(limit=5)
    assert isinstance(history, list)
    assert len(history) >= 2
