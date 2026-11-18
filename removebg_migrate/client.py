"""A small client for remove.bg-compatible APIs, using only the standard library.

    from removebg_migrate import RemoveBgClient

    client = RemoveBgClient(api_key="...", base_url="https://api.clearbg.org")
    result = client.remove_background("photo.jpg", size="full")
    open("photo.png", "wb").write(result.content)

It retries 429 and 503 responses after the number of seconds in Retry-After, and uses a
150-second timeout: requests are synchronous, and a compatible endpoint may wait on a GPU
for up to 90 seconds and retry once.
"""
import json
import mimetypes
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

DEFAULT_BASE_URL = "https://api.clearbg.org"
RETRY_STATUSES = {429, 503}


class ApiError(Exception):
    def __init__(self, status: int, errors: List[dict], headers: Dict[str, str]):
        self.status = status
        self.errors = errors
        self.headers = headers
        codes = ", ".join(e.get("code") or e.get("title", "?") for e in errors) or "unknown error"
        super().__init__(f"HTTP {status}: {codes}")

    @property
    def code(self) -> Optional[str]:
        return self.errors[0].get("code") if self.errors else None


@dataclass
class Result:
    content: bytes
    headers: Dict[str, str] = field(default_factory=dict)

    @property
    def credits_charged(self) -> Optional[float]:
        v = self.headers.get("x-credits-charged")
        return float(v) if v is not None else None

    @property
    def width(self) -> Optional[int]:
        v = self.headers.get("x-width")
        return int(v) if v else None

    @property
    def height(self) -> Optional[int]:
        v = self.headers.get("x-height")
        return int(v) if v else None

    @property
    def foreground_type(self) -> str:
        # remove.bg sent a category here; compatible APIs may not.
        return self.headers.get("x-type", "unknown")


def _multipart(fields: Dict[str, str], files: Dict[str, tuple]):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    for name, (filename, data, ctype) in files.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n".encode() + data + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


class RemoveBgClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 timeout: float = 150, max_retries: int = 4, sleep=time.sleep):
        self.api_key = api_key or os.environ.get("BG_API_KEY") or os.environ.get("CLEARBG_API_KEY")
        if not self.api_key:
            raise ValueError("Pass api_key or set BG_API_KEY.")
        self.base_url = (base_url or os.environ.get("BG_API_BASE") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._sleep = sleep

    def remove_background(self, image_path: Optional[str] = None, *, image_url: Optional[str] = None,
                          size: str = "full", **params) -> Result:
        """POST /v1.0/removebg. Extra keyword arguments are sent as form fields (format, bg_color, crop...)."""
        if (image_path is None) == (image_url is None):
            raise ValueError("Give exactly one of image_path or image_url.")
        fields = {"size": size, **{k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in params.items()}}
        files = {}
        if image_url:
            fields["image_url"] = image_url
        else:
            with open(image_path, "rb") as f:
                data = f.read()
            ctype = mimetypes.guess_type(image_path)[0] or "application/octet-stream"
            files["image_file"] = (os.path.basename(image_path), data, ctype)
        body, ctype = _multipart(fields, files)
        return self._request("POST", "/v1.0/removebg", body, ctype)

    def account(self) -> dict:
        """GET /v1.0/account: balance and free calls. Free on ClearBG."""
        return json.loads(self._request("GET", "/v1.0/account").content)

    def _request(self, method: str, path: str, body: Optional[bytes] = None, ctype: Optional[str] = None) -> Result:
        headers = {"X-Api-Key": self.api_key, "User-Agent": "removebg-migrate"}
        if ctype:
            headers["Content-Type"] = ctype
        attempt = 0
        while True:
            req = urllib.request.Request(self.base_url + path, data=body, method=method, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return Result(resp.read(), {k.lower(): v for k, v in resp.headers.items()})
            except urllib.error.HTTPError as e:
                hdrs = {k.lower(): v for k, v in e.headers.items()}
                raw = e.read()
                if e.code in RETRY_STATUSES and attempt < self.max_retries:
                    attempt += 1
                    self._sleep(_retry_after(hdrs, attempt))
                    continue
                try:
                    errors = json.loads(raw).get("errors", [])
                except ValueError:
                    errors = [{"title": raw[:200].decode("utf-8", "replace")}]
                raise ApiError(e.code, errors, hdrs) from None


def _retry_after(headers: Dict[str, str], attempt: int) -> float:
    try:
        return max(0.0, float(headers.get("retry-after", "")))
    except ValueError:
        return min(2.0 ** attempt, 30.0)
