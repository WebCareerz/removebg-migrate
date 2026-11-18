"""What changes when code written for the remove.bg v1.0 API is pointed at a compatible endpoint.

Each rule is one regular expression plus an explanation. The behaviour described here is that of
api.clearbg.org (https://clearbg.org/background-removal-api); most remove.bg-compatible services make
similar trade-offs, but check your provider's documentation.

Severity:
  change  -- must be edited for the migration (host, key, auth)
  error   -- the compatible endpoint will answer this request with an error
  check   -- works, but the result or a header differs from remove.bg
  info    -- accepted and ignored, or worth knowing
"""
import re
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class Rule:
    id: str
    severity: str
    pattern: "re.Pattern[str]"
    message: str
    # Optional filter on the captured value: return True when the value is a problem.
    bad_value: Optional[Callable[[str], bool]] = None
    # Message used when the parameter is present but its value is not a literal we can read.
    dynamic_message: Optional[str] = None


def _kv(key: str) -> "re.Pattern[str]":
    """Match `key` used as a request field in most languages, capturing a literal value if there is one.

    Covers  "key": "v"   key="v"   'key' => 'v'   ('key', 'v')   -F key=v   key=v&   key: v
    """
    return re.compile(
        r"""(?<![\w-])["']?""" + re.escape(key) + r"""["']?\s*(?:=>|[:=,])\s*(?:["']([^"'\n]*)["']|([\w.%#-]+))?""",
        re.IGNORECASE,
    )


def _norm(v: str) -> str:
    return v.strip().strip("\"'").lower()


ZERO = {"0", "0px", "0%"}
FULL_ROI = {"0% 0% 100% 100%", "0%0%100%100%"}
FALSEY = {"false", "0", "no", "none", ""}

RULES = [
    Rule(
        "host", "change", re.compile(r"api\.remove\.bg", re.IGNORECASE),
        "remove.bg host. Point it at your new endpoint (for example api.clearbg.org) and use that service's key. "
        "`removebg-migrate rewrite` can do this for you.",
    ),
    Rule(
        "oauth", "change",
        re.compile(r"""Authorization["']?\s*[:=,]\s*["']?Bearer|oauth""", re.IGNORECASE),
        "OAuth / bearer auth. Compatible endpoints such as ClearBG only accept the X-Api-Key header.",
    ),
    Rule(
        "improve", "error", re.compile(r"/v1\.0/improve", re.IGNORECASE),
        "/v1.0/improve (the feedback upload endpoint) is not part of most compatible APIs; ClearBG returns 404.",
    ),
    Rule(
        "bg_image", "error", re.compile(r"""(?<![\w-])["']?bg_image_(?:url|file)\b""", re.IGNORECASE),
        "Background images are not supported: the request returns 400 invalid_bg_image_url. "
        "Composite the transparent PNG yourself instead.",
    ),
    Rule(
        "add_shadow", "error", _kv("add_shadow"),
        "add_shadow=true returns 400 unsupported_shadow. Send false or leave it out.",
        bad_value=lambda v: _norm(v) not in FALSEY,
        dynamic_message="add_shadow is set from a variable: it must end up false, or the request returns 400.",
    ),
    Rule(
        "shadow_type", "error", _kv("shadow_type"),
        "shadow_type other than 'none' returns 400 unsupported_shadow.",
        bad_value=lambda v: _norm(v) not in FALSEY,
        dynamic_message="shadow_type is set from a variable: anything but 'none' returns 400.",
    ),
    Rule(
        "crop_margin", "error", _kv("crop_margin"),
        "crop_margin must be 0 (0, 0px or 0%); other values return 400 invalid_crop_margin. crop itself works.",
        bad_value=lambda v: _norm(v) not in ZERO,
        dynamic_message="crop_margin is set from a variable: only 0 is accepted.",
    ),
    Rule(
        "roi", "error", _kv("roi"),
        "roi must be the whole image ('0% 0% 100% 100%'); other regions return 400 invalid_roi.",
        bad_value=lambda v: _norm(v) not in FULL_ROI,
        dynamic_message="roi is set from a variable: only the whole image is accepted.",
    ),
    Rule(
        "scale", "error", _kv("scale"),
        "scale must be 'original'; other values return 400 invalid_scale.",
        bad_value=lambda v: _norm(v) != "original",
        dynamic_message="scale is set from a variable: only 'original' is accepted.",
    ),
    Rule(
        "position", "error", _kv("position"),
        "position must be 'original'; other values return 400 invalid_position.",
        bad_value=lambda v: _norm(v) != "original",
        dynamic_message="position is set from a variable: only 'original' is accepted.",
    ),
    Rule(
        "format_zip", "error", _kv("format"),
        "format=zip returns 400 invalid_format. Use png, webp or jpg.",
        bad_value=lambda v: _norm(v) == "zip",
    ),
    Rule(
        "bg_color_alpha", "error", _kv("bg_color"),
        "Semi-transparent bg_color (4 or 8 hex digits) returns 400 invalid_bg_color. Use 3 or 6 hex digits or a basic CSS colour name.",
        bad_value=lambda v: re.fullmatch(r"#?([0-9a-f]{4}|[0-9a-f]{8})", _norm(v)) is not None,
    ),
    Rule(
        "size_large", "check", _kv("size"),
        "Full-size output is capped at 25 megapixels (remove.bg allowed 50); larger images come back scaled to 25 MP.",
        bad_value=lambda v: _norm(v) in {"full", "4k", "auto", "50mp"},
    ),
    Rule(
        "x_type", "check", re.compile(r"""["']?X-Type["']?""", re.IGNORECASE),
        "The X-Type response header (foreground category) is not sent by ClearBG. Give it a default where you read it.",
    ),
    Rule(
        "credits_header", "info", re.compile(r"X-Credits-Charged", re.IGNORECASE),
        "X-Credits-Charged is an integer: 1 for a full image, 0 for a preview (remove.bg charged 0.25 per preview).",
    ),
    Rule(
        "ignored_fields", "info",
        re.compile(r"""(?<![\w-])["']?(?:type_level|semitransparency|shadow_opacity)["']?\s*(?:=>|[:=,])""", re.IGNORECASE),
        "Accepted and ignored: type_level, semitransparency and shadow_opacity don't change the result.",
    ),
]

SEVERITY_ORDER = {"change": 0, "error": 1, "check": 2, "info": 3}
