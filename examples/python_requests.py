"""Before/after with the requests library. The only edits are API_BASE and the key."""
import os

import requests

# API_BASE = "https://api.remove.bg"           # before
API_BASE = os.environ.get("BG_API_BASE", "https://api.clearbg.org")  # after

response = requests.post(
    f"{API_BASE}/v1.0/removebg",
    files={"image_file": open("photo.jpg", "rb")},
    data={"size": "full"},
    headers={"X-Api-Key": os.environ["BG_API_KEY"]},
    # Requests are synchronous; allow for a cold GPU plus one retry on the server side.
    timeout=150,
)
if response.status_code == 200:
    with open("photo-no-bg.png", "wb") as out:
        out.write(response.content)
    print("credits charged:", response.headers.get("X-Credits-Charged"))
    print("foreground type:", response.headers.get("X-Type", "unknown"))  # not sent by every provider
else:
    print(response.status_code, response.json()["errors"])
