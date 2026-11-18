"""Remove the background from every image in a folder, 4 at a time, skipping files already done.

    BG_API_KEY=... python examples/batch_folder.py photos/ out/

Re-running only processes what is missing, so an interrupted run can simply be started again.
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from removebg_migrate import ApiError, RemoveBgClient

src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
client = RemoveBgClient()  # BG_API_KEY, BG_API_BASE from the environment

jobs = []
for name in sorted(os.listdir(src)):
    if name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        out = os.path.join(dst, os.path.splitext(name)[0] + ".png")
        if not os.path.exists(out):
            jobs.append((os.path.join(src, name), out))


def run(job):
    path, out = job
    try:
        result = client.remove_background(path, size="full")
    except ApiError as e:
        return f"FAIL {path}: {e}"
    with open(out, "wb") as f:
        f.write(result.content)
    return f"ok   {path} -> {out} ({result.width}x{result.height})"


# 4 workers: ClearBG allows 4 images in progress per account; more just earns 429s.
with ThreadPoolExecutor(max_workers=4) as pool:
    for line in pool.map(run, jobs):
        print(line)
