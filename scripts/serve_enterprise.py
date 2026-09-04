"""AirSense Enterprise Platform Dedicated High-Performance Server (Port 8080)."""

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

app = FastAPI(title="AirSense Enterprise Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ENTERPRISE_HTML = Path(__file__).resolve().parent.parent / "apps" / "web_enterprise" / "index.html"

@app.get("/", include_in_schema=False)
@app.get("/enterprise", include_in_schema=False)
async def serve_enterprise():
    return FileResponse(ENTERPRISE_HTML, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="warning")
