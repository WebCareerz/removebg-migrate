"""removebg-migrate: scan, rewrite and try a remove.bg-compatible API."""
import argparse
import json
import sys
from collections import Counter

from . import __version__
from .client import DEFAULT_BASE_URL, ApiError, RemoveBgClient
from .rewrite import rewrite
from .scan import scan

LABEL = {"change": "CHANGE", "error": "ERROR ", "check": "CHECK ", "info": "INFO  "}


def cmd_scan(args) -> int:
    findings = scan(args.path)
    if args.json:
        print(json.dumps([f.__dict__ for f in findings], indent=2))
    else:
        if not findings:
            print("No remove.bg API usage found.")
            return 0
        for f in findings:
            if f.severity == "info" and not args.verbose:
                continue
            print(f"{LABEL[f.severity]} {f.path}:{f.line}  [{f.rule}]")
            print(f"        {f.text}")
            print(f"        -> {f.message}")
        counts = Counter(f.severity for f in findings)
        summary = ", ".join(f"{counts[s]} {s}" for s in ("change", "error", "check", "info") if counts[s])
        print(f"\n{summary}" + ("" if args.verbose else "  (use -v to show info)"))
    return 1 if any(f.severity == "error" for f in findings) and args.strict else 0


def cmd_rewrite(args) -> int:
    changes = rewrite(args.path, args.to, write=args.write)
    if not changes:
        print("Nothing to rewrite: no api.remove.bg found.")
        return 0
    for path, count, diff in changes:
        if not args.write:
            sys.stdout.write(diff)
        print(f"{'rewrote' if args.write else 'would rewrite'} {path} ({count} replacement{'s' if count != 1 else ''})")
    if not args.write:
        print("\nDry run. Add --write to apply. Remember to switch the API key too.")
    return 0


def cmd_try(args) -> int:
    client = RemoveBgClient(api_key=args.key, base_url=args.base_url)
    if "remove.bg" in client.base_url and args.size == "preview":
        print("note: on api.remove.bg a preview costs 0.25 credits.", file=sys.stderr)
    try:
        if args.image.startswith(("http://", "https://")):
            result = client.remove_background(image_url=args.image, size=args.size)
        else:
            result = client.remove_background(args.image, size=args.size)
    except ApiError as e:
        print(f"{e}", file=sys.stderr)
        for err in e.errors:
            print(f"  {err.get('code')}: {err.get('title')} {err.get('detail') or ''}", file=sys.stderr)
        return 2
    with open(args.out, "wb") as f:
        f.write(result.content)
    print(f"saved {args.out}  {result.width}x{result.height}  credits charged: {result.credits_charged}")
    for h in ("x-ratelimit-limit", "x-ratelimit-remaining", "x-type"):
        print(f"  {h}: {result.headers.get(h, '(not sent)')}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="removebg-migrate", description=__doc__)
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="find remove.bg API calls and options that won't carry over")
    s.add_argument("path", nargs="?", default=".")
    s.add_argument("-v", "--verbose", action="store_true", help="also show info-level notes")
    s.add_argument("--json", action="store_true", help="machine-readable output")
    s.add_argument("--strict", action="store_true", help="exit 1 if any error-level finding (for CI)")
    s.set_defaults(func=cmd_scan)

    r = sub.add_parser("rewrite", help="replace api.remove.bg with another host (dry run by default)")
    r.add_argument("path", nargs="?", default=".")
    r.add_argument("--to", default=DEFAULT_BASE_URL, help=f"new host (default {DEFAULT_BASE_URL})")
    r.add_argument("--write", action="store_true", help="apply the changes")
    r.set_defaults(func=cmd_rewrite)

    t = sub.add_parser("try", help="send one image to a compatible endpoint and show the response headers")
    t.add_argument("image", help="local file or http(s) URL")
    t.add_argument("--key", help="API key (or set BG_API_KEY)")
    t.add_argument("--base-url", default=None, help=f"default {DEFAULT_BASE_URL}")
    t.add_argument("--size", default="preview", help="preview (default, free on ClearBG) or full")
    t.add_argument("-o", "--out", default="no-bg.png")
    t.set_defaults(func=cmd_try)

    args = p.parse_args(argv)
    return args.func(args)
