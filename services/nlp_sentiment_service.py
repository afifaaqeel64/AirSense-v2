import re
from typing import Dict, Any, List

class NLPSentimentService:
    """
    Multi-variable sentiment analysis and NLP extraction module.
    Interprets the severity and urgency of government mandates and business impact reports.
    """
    def __init__(self):
        # Basic keyword dictionaries for demonstration
        self.closure_keywords = ["closed", "shutdown", "holiday", "suspended", "banned"]
        self.advisory_keywords = ["advised", "recommended", "caution", "restricted"]
        self.severity_multipliers = {
            "severe": 2.0,
            "extreme": 2.5,
            "hazardous": 3.0,
            "moderate": 1.0
        }

    def extract_policy_details(self, text: str) -> Dict[str, Any]:
        """
        Extract Event Type, Notice Time, Enforcement Time, and Affected Sectors from raw text.
        """
        text_lower = text.lower()
        
        # Determine event type
        event_type = "Advisory"
        if any(word in text_lower for word in self.closure_keywords):
            event_type = "Closure"
            
        # Determine affected sectors
        sectors = []
        if "school" in text_lower or "college" in text_lower or "university" in text_lower:
            sectors.append("Education")
        if "motorway" in text_lower or "traffic" in text_lower or "highway" in text_lower:
            sectors.append("Transport")
        if "industry" in text_lower or "factory" in text_lower:
            sectors.append("Industrial")
            
        return {
            "event_type": event_type,
            "affected_sectors": sectors,
            "extracted_lead_time_hours": 24 # Stubbed: ideally parsed from date/time regex
        }

    def calculate_disruption_score(self, texts: List[str]) -> Dict[str, float]:
        """
        Calculates a disruption score based on business news sentiment.
        Returns a score from 0-100.
        """
        total_score = 0.0
        for text in texts:
            text_lower = text.lower()
            score = 10.0
            
            # Apply severity multipliers
            for word, multiplier in self.severity_multipliers.items():
                if word in text_lower:
                    score *= multiplier
                    
            if "drop" in text_lower or "loss" in text_lower or "disrupt" in text_lower:
                score += 30.0
                
            total_score += score
            
        # Normalize to 0-100
        normalized_score = min(100.0, max(0.0, total_score / max(len(texts), 1)))
        
        return {
            "disruption_score": normalized_score,
            "confidence": 0.85
        }

if __name__ == "__main__":
    nlp = NLPSentimentService()
    print(nlp.extract_policy_details("Attention: Due to severe smog, all public schools will be closed."))
    print(nlp.calculate_disruption_score(["Supply chains heavily disrupted today. Significant loss reported."]))
