import requests
import json
import time

# Configuration
LOCAL_URL = "http://127.0.0.1:8000"
PROD_URL = "https://smartvenue-backend-623281650123.us-central1.run.app"

def run_checks(base_url, name):
    print(f"\n--- Testing {name} ({base_url}) ---")
    
    # 1. Basic Health Check
    try:
        r = requests.get(f"{base_url}/health", timeout=5)
        print(f"[Health] Status: {r.status_code} | Body: {r.json()}")
    except Exception as e:
        print(f"[Health] FAILED: {e}")

    # 2. Graph Endpoint (Public-ish)
    try:
        r = requests.get(f"{base_url}/api/graph", timeout=5)
        print(f"[Graph] Status: {r.status_code}")
        if r.status_code == 200:
            nodes = r.json().get('nodes', [])
            print(f"       Found {len(nodes)} nodes in the georeferenced graph.")
    except Exception as e:
        print(f"[Graph] FAILED: {e}")

    # 3. Secure Zones Endpoint (Expect 401 without token)
    try:
        r = requests.get(f"{base_url}/api/zones", timeout=5)
        print(f"[Zones] Status: {r.status_code} (Expected 401 if unauthorized)")
    except Exception as e:
        print(f"[Zones] FAILED: {e}")

if __name__ == "__main__":
    run_checks(LOCAL_URL, "Local Backend")
    # run_checks(PROD_URL, "Production Backend") # Uncomment to test prod
