"""AirSense Pakistan - Universal Cloud Entrypoint (Hugging Face Spaces & Cloud PaaS).

Binds the production FastAPI application to port 7860 (Hugging Face standard)
or the $PORT environment variable, serving the full multi-campus intelligence
engine, real-time sensor ingestion routes, and 24/7 background scheduler.
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import uvicorn
from apps.api.main import app

PORT = int(os.getenv("PORT", 7860))
HOST = "0.0.0.0"

if __name__ == "__main__":
    print(f"[AirSense Cloud Ingress] Launching AirSense Pakistan on {HOST}:{PORT}...")
    uvicorn.run(app, host=HOST, port=PORT)
