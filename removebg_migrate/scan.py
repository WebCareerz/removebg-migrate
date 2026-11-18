"""Find remove.bg API usage in a codebase and report what will change after a migration."""
import os
import re
from dataclasses import dataclass
from typing import Iterable, Iterator, List

from .rules import RULES, SEVERITY_ORDER, Rule

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "vendor", ".venv", "venv", "env", "__pycache__",
    "dist", "build", ".next", ".nuxt", ".tox", ".mypy_cache", ".pytest_cache", "target",
}
TEXT_EXT = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".php", ".rb", ".go", ".java", ".kt", ".kts",
    ".cs", ".swift", ".rs", ".sh", ".bash", ".zsh", ".ps1", ".env", ".ini", ".cfg", ".conf", ".toml",
    ".yaml", ".yml", ".json", ".md", ".txt", ".dart", ".scala", ".ex", ".exs", ".lua", ".pl", ".r",
}
MAX_BYTES = 2_000_000

# A file only gets parameter checks when it talks to remove.bg; otherwise words like
# "position" or "size" would match ordinary code everywhere.
CONTEXT = re.compile(r"remove\.bg|/v1\.0/removebg|removebg", re.IGNORECASE)
CONTEXT_FREE_RULES = {"host"}

# Unquoted values are only trusted when they look like a literal for these fields.
LITERAL = re.compile(
    r"^(true|false|none|zip|png|jpg|jpeg|webp|auto|0|0px|0%|original|full|4k|50mp|preview|small|regular|medium|hd"
    r"|#?[0-9a-f]{3}|#?[0-9a-f]{4}|#?[0-9a-f]{6}|#?[0-9a-f]{8})$",
    re.IGNORECASE,
)


@dataclass
class Finding:
    path: str
    line: int
    rule: str
    severity: str
    message: str
    text: str


def iter_files(root: str) -> Iterator[str]:
    if os.path.isfile(root):
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            ext = os.path.splitext(name)[1].lower()
            if ext in TEXT_EXT or name in {"Dockerfile", ".env"} or name.startswith(".env"):
                yield os.path.join(dirpath, name)


def read_text(path: str):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return None
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    return data.decode("utf-8", errors="replace")


def _value(m: "re.Match[str]"):
    """Return (literal value or None, is_dynamic)."""
    if m.lastindex is None:
        return None, True
    quoted, bare = m.group(1), m.group(2)
    if quoted is not None:
        return quoted, False
    if bare is None:
        return None, True
    # -F 'key=value', key=value&other=... and ?key=value are literal form/query strings.
    whole = m.group(0)
    before = m.string[m.start() - 1] if m.start() > 0 else ""
    form_style = "=" in whole and ":" not in whole and (whole[0] in "'\"" or (before != "" and before in "&?'\""))
    if form_style or LITERAL.match(bare):
        return bare, False
    return None, True


def _check_line(rule: Rule, line: str) -> Iterable[str]:
    for m in rule.pattern.finditer(line):
        if rule.bad_value is None:
            yield rule.message
            return
        value, dynamic = _value(m)
        if dynamic:
            if rule.dynamic_message:
                yield rule.dynamic_message
                return
            continue
        if rule.bad_value(value):
            yield rule.message
            return


def scan_text(path: str, text: str) -> List[Finding]:
    in_context = CONTEXT.search(text) is not None
    findings = []
    for n, line in enumerate(text.splitlines(), 1):
        for rule in RULES:
            if not in_context and rule.id not in CONTEXT_FREE_RULES:
                continue
            for msg in _check_line(rule, line):
                findings.append(Finding(path, n, rule.id, rule.severity, msg, line.strip()[:160]))
    return findings


def scan(root: str) -> List[Finding]:
    out: List[Finding] = []
    for path in iter_files(root):
        text = read_text(path)
        if text is None or not text:
            continue
        out.extend(scan_text(path, text))
    out.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.path, f.line))
    return out
