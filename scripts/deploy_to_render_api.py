"""AirSense Pakistan - Automated Deployment via Render REST API"""
import sys, time, json, urllib.request, urllib.error

RENDER_API_BASE = "https://api.render.com/v1"

def render_request(method: str, endpoint: str, api_key: str, data: dict = None):
    url = f"{RENDER_API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "AirSense-Deployer/1.0"
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        print(f"[RENDER API ERROR] HTTP {e.code} on {method} {endpoint}: {err_body}")
        raise

def get_owner_id(api_key: str) -> str:
    print("[1/5] Authenticating with Render API...")
    owners = render_request("GET", "/owners", api_key)
    if not owners:
        raise ValueError("No workspaces/owners found for this Render API key.")
    owner = owners[0].get("owner", owners[0])
    owner_id = owner.get("id")
    owner_name = owner.get("name") or owner.get("email")
    print(f"      Authenticated as: {owner_name} (ID: {owner_id})")
    return owner_id

def get_or_create_database(api_key: str, owner_id: str) -> str:
    print("[2/5] Checking PostgreSQL database (airsense-db)...")
    postgres_list = render_request("GET", f"/postgres?ownerId={owner_id}", api_key)
    for pg in postgres_list:
        pg_item = pg.get("postgres", pg)
        if pg_item.get("name") == "airsense-db":
            print(f"      Found existing database airsense-db (ID: {pg_item.get('id')})")
            return pg_item.get("id")
    print("      Creating managed PostgreSQL database airsense-db (plan: free, region: singapore)...")
    payload = {
        "name": "airsense-db",
        "ownerId": owner_id,
        "plan": "free",
        "region": "singapore",
        "databaseName": "airsense",
        "databaseUser": "airsense"
    }
    new_pg = render_request("POST", "/postgres", api_key, payload)
    pg_id = new_pg.get("id")
    print(f"      Database created successfully! (ID: {pg_id})")
    return pg_id

def deploy_web_service(api_key: str, owner_id: str, repo_url: str, branch: str = "main"):
    print(f"[3/5] Setting up Web Service from repository: {repo_url}...")
    services = render_request("GET", f"/services?ownerId={owner_id}", api_key)
    service_id = None
    existing_url = None
    for s in services:
        svc = s.get("service", s)
        if svc.get("name") == "airsense-api":
            service_id = svc.get("id")
            existing_url = svc.get("serviceDetails", {}).get("url")
            print(f"      Found existing service airsense-api (ID: {service_id})")
            break
    if not service_id:
        print("      Registering new Web Service airsense-api...")
        payload = {
            "type": "web_service",
            "name": "airsense-api",
            "ownerId": owner_id,
            "repo": repo_url,
            "branch": branch,
            "autoDeploy": "yes",
            "serviceDetails": {
                "env": "python",
                "plan": "free",
                "region": "singapore",
                "buildCommand": "pip install -r requirements.txt",
                "startCommand": "sh -c \"uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}\"",
                "healthCheckPath": "/api/v1/health/liveness",
                "envVars": [
                    {"key": "AIR_SENSE_ENV", "value": "production"},
                    {"key": "AIR_SENSE_TIMEZONE", "value": "Asia/Karachi"},
                    {"key": "BACKGROUND_SCHEDULER_ENABLED", "value": "true"},
                    {"key": "CORS_ORIGINS", "value": "https://airsense-team.vercel.app,http://localhost:3000"}
                ]
            }
        }
        new_svc = render_request("POST", "/services", api_key, payload)
        service_id = new_svc.get("id")
        existing_url = new_svc.get("serviceDetails", {}).get("url")
        print(f"      Service created! (ID: {service_id})")
    print("[4/5] Triggering production deployment on Render...")
    deploy = render_request("POST", f"/services/{service_id}/deploys", api_key, {"clearCache": "do_not_clear"})
    deploy_id = deploy.get("id")
    print(f"      Deployment launched (Deploy ID: {deploy_id})")
    print("[5/5] Monitoring build and deployment progress...")
    for _ in range(60):
        time.sleep(5)
        d_status = render_request("GET", f"/services/{service_id}/deploys/{deploy_id}", api_key)
        status = d_status.get("status")
        print(f"      Status: {status.upper()}...")
        if status == "live":
            svc_info = render_request("GET", f"/services/{service_id}", api_key)
            live_url = svc_info.get("serviceDetails", {}).get("url") or existing_url
            print("\n" + "=" * 70)
            print("  DEPLOYMENT SUCCESSFUL!")
            print(f"  Live AirSense Platform URL: {live_url}")
            print(f"  Frontend Dashboard:         {live_url}/")
            print(f"  Command Center:             {live_url}/command")
            print(f"  Sensor Diagnostics:         {live_url}/diagnostics")
            print(f"  24/7 Weather Feed:          {live_url}/opensource")
            print(f"  API Liveness Probe:         {live_url}/api/v1/health/liveness")
            print("=" * 70)
            return live_url
        elif status in ["build_failed", "update_failed", "canceled"]:
            raise RuntimeError(f"Deployment ended with status: {status}")
    print("\nDeployment is building in background. Check Render dashboard.")
    return existing_url

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: py scripts/deploy_to_render_api.py <RENDER_API_KEY> <GITHUB_REPO_URL> [BRANCH]")
        sys.exit(1)
    owner_id = get_owner_id(sys.argv[1])
    get_or_create_database(sys.argv[1], owner_id)
    deploy_web_service(sys.argv[1], owner_id, sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "main")
