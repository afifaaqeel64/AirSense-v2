import pytest
from services.nlp_sentiment_service import NLPSentimentService

def test_extract_policy_details_closure():
    nlp = NLPSentimentService()
    text = "Attention: Due to severe smog, all public schools will be closed tomorrow."
    result = nlp.extract_policy_details(text)
    
    assert result["event_type"] == "Closure"
    assert "Education" in result["affected_sectors"]

def test_extract_policy_details_advisory():
    nlp = NLPSentimentService()
    text = "General advisory: Drive with caution on Motorway M-2 due to moderate fog."
    result = nlp.extract_policy_details(text)
    
    assert result["event_type"] == "Advisory"
    assert "Transport" in result["affected_sectors"]

def test_calculate_disruption_score():
    nlp = NLPSentimentService()
    texts = ["Supply chains heavily disrupted today. Significant loss reported."]
    result = nlp.calculate_disruption_score(texts)
    
    # 10.0 base score
    # + 30.0 for "loss" or "disrupt"
    # total 40.0
    assert result["disruption_score"] == 40.0
    assert result["confidence"] == 0.85
