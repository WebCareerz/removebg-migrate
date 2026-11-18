import os
import requests

REMOVE_BG_URL = "https://api.remove.bg/v1.0/removebg"


def cutout(path, shadow):
    resp = requests.post(
        REMOVE_BG_URL,
        files={"image_file": open(path, "rb")},
        data={
            "size": "full",
            "format": "zip",
            "bg_color": "ffffff80",
            "crop": "true",
            "crop_margin": "10%",
            "add_shadow": shadow,
            "semitransparency": "true",
        },
        headers={"X-Api-Key": os.environ["REMOVE_BG_KEY"]},
    )
    category = resp.headers["X-Type"]
    return resp.content, category
