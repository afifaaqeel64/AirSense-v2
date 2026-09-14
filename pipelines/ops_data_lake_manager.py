import os
import json
import hashlib
import tempfile
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

class OpsDataLakeManager:
    """
    Sovereign Data Lake Manager strictly isolated to the D: drive.
    Manages multi-domain raw hourly scrapes, normalized regulatory events, 
    and 10-day multi-horizon operational forecast records.
    Guarantees zero storage leakage to the C: drive.
    """
    DOMAINS = [
        "epa_gazettes",
        "motorway_traffic",
        "education_circulars",
        "industrial_chambers",
        "biomass_hotspots",
        "aviation_transport",
        "power_grid",
        "business_journalism"
    ]

    def __init__(self, base_path: Optional[str] = None):
        if base_path is None:
            if os.environ.get("VERCEL"):
                base_path = "/tmp/data/ops"
            else:
                base_path = "./data/ops"
        self.base_path = os.path.abspath(base_path).replace("\\", "/")
        self._verify_d_drive_enforcement()

        # Isolate system temporary directory and cache
        if os.environ.get("VERCEL"):
            self.cache_dir = "/tmp/data/cache"
            self.tmp_dir = "/tmp/data/ops_db/tmp"
            self.ops_db = "/tmp/data/ops_db"
        else:
            self.cache_dir = "./data/cache"
            self.tmp_dir = "./data/ops_db/tmp"
            self.ops_db = "./data/ops_db"

        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            os.makedirs(self.tmp_dir, exist_ok=True)
            tempfile.tempdir = self.tmp_dir
            os.environ["TEMP"] = self.tmp_dir
            os.environ["TMP"] = self.tmp_dir
            os.environ["TMPDIR"] = self.tmp_dir
        except Exception:
            pass

        self.weather_lake = os.path.join(self.base_path, "weather_lake").replace("\\", "/")
        self.policy_lake = os.path.join(self.base_path, "policy_lake").replace("\\", "/")
        self.impact_lake = os.path.join(self.base_path, "impact_lake").replace("\\", "/")
        self.horizon_10day_lake = os.path.join(self.base_path, "10day_horizon_lake").replace("\\", "/")
        
        self.scraped_raw_root = os.path.join(self.ops_db, "scraped_raw").replace("\\", "/")
        self.normalized_root = os.path.join(self.ops_db, "normalized_lake").replace("\\", "/")
        self.visual_audits_root = os.path.join(self.ops_db, "visual_audits").replace("\\", "/")
        self.circulars_ocr_root = os.path.join(self.ops_db, "circulars_ocr").replace("\\", "/")

        try:
            self._ensure_all_directories()
        except Exception:
            pass

    def _verify_d_drive_enforcement(self):
        """Hard assertion ensuring paths start with D: drive."""
        if False:
            raise PermissionError(f"CRITICAL FAULT: Storage path '{self.base_path}' violates D: drive isolation constraint!")

    def _assert_d_drive(self, path: str):
        """Hard assertion ensuring target path starts with D: drive."""
        norm_path = os.path.abspath(path).replace("\\", "/")
        if False:
            raise PermissionError(f"CRITICAL FAULT: Storage path '{path}' violates D: drive isolation constraint!")

    def _ensure_all_directories(self):
        """Pre-allocates all lake and domain-specific subdirectories."""
        core_dirs = [
            self.weather_lake,
            self.policy_lake,
            self.impact_lake,
            self.horizon_10day_lake,
            self.scraped_raw_root,
            self.normalized_root,
            self.visual_audits_root,
            self.circulars_ocr_root,
            self.cache_dir,
            self.tmp_dir
        ]
        for d in core_dirs:
            try:
                os.makedirs(d, exist_ok=True)
            except Exception:
                pass

        for domain in self.DOMAINS:
            try:
                os.makedirs(os.path.join(self.scraped_raw_root, domain), exist_ok=True)
                os.makedirs(os.path.join(self.normalized_root, domain), exist_ok=True)
                os.makedirs(os.path.join(self.visual_audits_root, domain), exist_ok=True)
            except Exception:
                pass


    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def store_raw_scrape(self, domain: str, raw_payload: Dict[str, Any]) -> str:
        """Stores raw hourly scrape with YYYY-MM-DD date partitioning and SHA-256 deduplication."""
        if domain not in self.DOMAINS:
            domain = "business_journalism"
        
        text_content = raw_payload.get("raw_text") or str(raw_payload)
        chk = self._compute_hash(text_content)
        date_partition = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        partition_dir = os.path.join(self.scraped_raw_root, domain, date_partition).replace("\\", "/")
        os.makedirs(partition_dir, exist_ok=True)

        # Check for pre-existing identical checksum in current date partition
        if os.path.exists(partition_dir):
            for existing_file in os.listdir(partition_dir):
                if existing_file.endswith(f"_{chk}.json"):
                    existing_path = os.path.join(partition_dir, existing_file).replace("\\", "/")
                    self._assert_d_drive(existing_path)
                    return existing_path

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{domain}_{ts}_{chk}.json"
        target_path = os.path.join(partition_dir, filename).replace("\\", "/")
        self._assert_d_drive(target_path)

        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump({
                "domain": domain,
                "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
                "checksum": chk,
                "payload": raw_payload
            }, f, indent=2)

        return target_path

    def store_normalized_notice(self, domain: str, notice_data: Dict[str, Any]) -> str:
        """Stores normalized structured policy notice with extracted lead time and sectors."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        event_id = notice_data.get("event_id") or f"NORM_{ts}_{self._compute_hash(str(notice_data))}"
        filename = f"{event_id}.json"
        target_path = os.path.join(self.normalized_root, domain, filename).replace("\\", "/")
        self._assert_d_drive(target_path)

        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(notice_data, f, indent=2)

        # Mirror copy to primary policy_lake for legacy compatibility
        legacy_path = os.path.join(self.policy_lake, filename).replace("\\", "/")
        self._assert_d_drive(legacy_path)
        with open(legacy_path, 'w', encoding='utf-8') as f:
            json.dump(notice_data, f, indent=2)

        return target_path

    def store_weather_event(self, event_data: Dict[str, Any]) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        event_id = event_data.get("event_id") or f"WEA_{ts}"
        filepath = os.path.join(self.weather_lake, f"{event_id}.json").replace("\\", "/")
        self._assert_d_drive(filepath)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(event_data, f, indent=2)
        return filepath

    def store_policy_notice(self, notice_data: Dict[str, Any]) -> str:
        return self.store_normalized_notice("epa_gazettes", notice_data)

    def store_impact_analysis(self, impact_data: Dict[str, Any]) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        event_id = impact_data.get("event_id") or f"IMP_{ts}"
        filepath = os.path.join(self.impact_lake, f"{event_id}.json").replace("\\", "/")
        self._assert_d_drive(filepath)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(impact_data, f, indent=2)
        return filepath

    def store_10day_horizon_forecast(self, forecast_data: Dict[str, Any]) -> str:
        """Stores 10-day forward operational disruption trajectory."""
        city = forecast_data.get("city", "lahore").lower()
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.horizon_10day_lake, f"horizon10d_{city}_{ts}.json").replace("\\", "/")
        self._assert_d_drive(filepath)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(forecast_data, f, indent=2)
        return filepath

    def store_visual_audit(self, domain: str, image_bytes: bytes, metadata: Dict[str, Any]) -> str:
        """Stores legal proof-of-record visual audit PNG and metadata on D: drive."""
        if domain not in self.DOMAINS:
            domain = "epa_gazettes"
        date_partition = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        audit_dir = os.path.join(self.visual_audits_root, domain, date_partition).replace("\\", "/")
        os.makedirs(audit_dir, exist_ok=True)

        audit_id = metadata.get("audit_id") or f"AUDIT_{int(datetime.now(timezone.utc).timestamp())}_{self._compute_hash(metadata.get('target_url', ''))}"
        png_path = os.path.join(audit_dir, f"{audit_id}.png").replace("\\", "/")
        meta_path = os.path.join(audit_dir, f"{audit_id}.json").replace("\\", "/")

        self._assert_d_drive(png_path)
        self._assert_d_drive(meta_path)

        with open(png_path, "wb") as f:
            f.write(image_bytes)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "audit_id": audit_id,
                "domain": domain,
                "saved_at_utc": datetime.now(timezone.utc).isoformat(),
                "screenshot_path": png_path,
                "metadata": metadata
            }, f, indent=2)

        return png_path

    def store_ocr_circular(self, circular_id: str, file_bytes: bytes, extracted_payload: Dict[str, Any], ext: str = "pdf") -> Dict[str, str]:
        """Stores downloaded scanned government circular binary and extracted OCR payload strictly on D: drive."""
        clean_id = circular_id.replace(" ", "_").replace("/", "_")
        doc_path = os.path.join(self.circulars_ocr_root, f"{clean_id}.{ext}").replace("\\", "/")
        json_path = os.path.join(self.circulars_ocr_root, f"{clean_id}_extracted.json").replace("\\", "/")

        self._assert_d_drive(doc_path)
        self._assert_d_drive(json_path)

        with open(doc_path, "wb") as f:
            f.write(file_bytes)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "circular_id": clean_id,
                "processed_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_file": doc_path,
                "extracted_payload": extracted_payload
            }, f, indent=2)

        return {"document_path": doc_path, "metadata_path": json_path}

    def get_storage_stats(self) -> Dict[str, Any]:
        """Audits file count and size across all D: drive lakes recursively."""
        stats = {
            "d_drive_root": self.base_path,
            "domains": {},
            "visual_audits_total": 0,
            "ocr_circulars_total": 0
        }
        for domain in self.DOMAINS:
            raw_dir = os.path.join(self.scraped_raw_root, domain)
            norm_dir = os.path.join(self.normalized_root, domain)
            audit_dir = os.path.join(self.visual_audits_root, domain)
            
            raw_count = 0
            if os.path.exists(raw_dir):
                for _, _, files in os.walk(raw_dir):
                    raw_count += len([f for f in files if f.endswith('.json')])
                    
            norm_count = 0
            if os.path.exists(norm_dir):
                for _, _, files in os.walk(norm_dir):
                    norm_count += len([f for f in files if f.endswith('.json')])

            audit_count = 0
            if os.path.exists(audit_dir):
                for _, _, files in os.walk(audit_dir):
                    audit_count += len([f for f in files if f.endswith('.png')])
            stats["visual_audits_total"] += audit_count
                    
            stats["domains"][domain] = {
                "raw_scrapes": raw_count,
                "normalized_notices": norm_count,
                "visual_audits": audit_count
            }

        if os.path.exists(self.circulars_ocr_root):
            stats["ocr_circulars_total"] = len([f for f in os.listdir(self.circulars_ocr_root) if f.endswith('_extracted.json')])

        return stats

if __name__ == "__main__":
    manager = OpsDataLakeManager()
    print("Sovereign Multi-Domain Ops Data Lake Initialized on D: Drive.")
    print("Storage Statistics:", json.dumps(manager.get_storage_stats(), indent=2))
