"""Starts the API (inside the container only) and then the Streamlit UI on port 7860."""
import os
import subprocess
import sys
import time
import urllib.request

api = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "api:app", "--app-dir", "src", "--host", "127.0.0.1", "--port", "8000"]
)

# Wait until the API has loaded its models and answers /health
print("Waiting for the API to start...", flush=True)
for _ in range(180):
    if api.poll() is not None:
        sys.exit("API process stopped unexpectedly")
    try:
        urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2)
        print("API is ready.", flush=True)
        break
    except Exception:
        time.sleep(2)
else:
    api.terminate()
    sys.exit("API did not start in time")

ui = subprocess.Popen(
    [
        sys.executable, "-m", "streamlit", "run", "src/app.py",
        "--server.port", os.getenv("PORT", "7860"),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--server.enableXsrfProtection", "false",
        "--server.enableCORS", "false",
        "--browser.gatherUsageStats", "false",
    ]
)

# If either process stops, stop the container so it gets restarted
while api.poll() is None and ui.poll() is None:
    time.sleep(2)
api.terminate()
ui.terminate()
sys.exit(1)