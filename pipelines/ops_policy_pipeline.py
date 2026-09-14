import os
import sys
from typing import Dict, Any, List

# Ensure project root in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from pipelines.ops_data_lake_manager import OpsDataLakeManager
from services.scraping_orchestrator import ScrapingOrchestrator
from services.nlp_sentiment_service import NLPSentimentService

class OpsPolicyPipeline:
    """
    Sovereign Regulatory & Policy Multi-Pipeline.
    Reverse-engineers government Section 144 orders, NH&MP Motorway closures,
    School Education Department circulars, and EPA industrial notices.
    """
    def __init__(self):
        self.lake_manager = OpsDataLakeManager()
        self.orchestrator = ScrapingOrchestrator()
        self.nlp = NLPSentimentService()
        
    def run_pipeline(self) -> List[Dict[str, Any]]:
        """Executes targeted multi-domain scrapers and normalizes regulatory notices."""
        domains_to_sweep = [
            "epa_gazettes",
            "motorway_traffic",
            "education_circulars",
            "industrial_chambers",
            "biomass_hotspots",
            "aviation_transport",
            "power_grid",
            "business_journalism"
        ]
        
        processed_notices = []
        for domain in domains_to_sweep:
            try:
                res = self.orchestrator.scrape_domain(domain)
                rec = res.get("record", {})
                processed_notices.append(rec)
            except Exception as e:
                print(f"Policy pipeline notice capture warning on {domain}: {e}")
                
        return processed_notices

    def get_radar_summary(self) -> Dict[str, Any]:
        """Returns live multi-domain scraping radar status."""
        return self.orchestrator.get_radar_status()

if __name__ == "__main__":
    pipeline = OpsPolicyPipeline()
    notices = pipeline.run_pipeline()
    print(f"Policy pipeline extracted {len(notices)} structured regulatory notices.")
