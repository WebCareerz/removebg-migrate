"""Replace the remove.bg API host with another host, as a dry-run diff by default."""
import difflib
import re
from typing import List, Tuple

from .scan import iter_files, read_text

HOST = re.compile(r"api\.remove\.bg", re.IGNORECASE)


def rewrite_text(text: str, new_host: str) -> Tuple[str, int]:
    return HOST.subn(new_host, text)


def rewrite(root: str, new_host: str, write: bool = False) -> List[Tuple[str, int, str]]:
    """Return (path, replacements, unified diff) for every file that would change."""
    new_host = re.sub(r"^https?://", "", new_host).rstrip("/")
    changes = []
    for path in iter_files(root):
        text = read_text(path)
        if not text or not HOST.search(text):
            continue
        new, count = rewrite_text(text, new_host)
        diff = "".join(difflib.unified_diff(
            text.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile=f"a/{path}", tofile=f"b/{path}",
        ))
        if write:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new)
        changes.append((path, count, diff))
    return changes
