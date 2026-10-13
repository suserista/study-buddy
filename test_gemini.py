# Diagnostic tool: checks which Gemini models currently respond.
# No secrets inside — safe to keep in the repo.
# Keep the MODELS list in sync with GEMINI_MODELS in app.py.
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()
key = os.environ.get("GEMINI_API_KEY", "")
print("Key loaded:", "yes" if key else "NO")

MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
]

for model in MODELS:
    start = time.time()
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": key},
            json={"contents": [{"parts": [{"text": "Reply with exactly: OK"}]}]},
            timeout=20)
        dt = round(time.time() - start, 1)
        if r.status_code == 200:
            print(f"{model}: WORKS ({dt}s)")
        else:
            print(f"{model}: HTTP {r.status_code} ({dt}s)")
    except Exception as e:
        print(f"{model}: FAILED - {type(e).__name__}")