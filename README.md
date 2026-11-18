# removebg-migrate

Find the remove.bg API calls in your code, see which options won't carry over to a compatible endpoint, and switch the host in one command.

remove.bg's standalone website and self-service API close on **December 1, 2026**, and unused pay-as-you-go credits expire that day. API users are pointed to Leonardo.Ai, which means rewriting the call. If your code posts images to `/v1.0/removebg`, moving to an endpoint that accepts the same request is usually a host and key change, plus a few options to check. This tool does the checking.

```python
# src/cutout.py
REMOVE_BG_URL = "https://api.remove.bg/v1.0/removebg"

def cutout(path, shadow):
    resp = requests.post(
        REMOVE_BG_URL,
        files={"image_file": open(path, "rb")},
        data={"size": "full", "format": "zip", "add_shadow": shadow},
        headers={"X-Api-Key": os.environ["REMOVE_BG_KEY"]},
    )
    return resp.content, resp.headers["X-Type"]
```

```
$ removebg-migrate scan src/
CHANGE src/cutout.py:4  [host]
        REMOVE_BG_URL = "https://api.remove.bg/v1.0/removebg"
        -> remove.bg host. Point it at your new endpoint (for example api.clearbg.org) and use that service's key. `removebg-migrate rewrite` can do this for you.
ERROR  src/cutout.py:11  [add_shadow]
        data={"size": "full", "format": "zip", "add_shadow": shadow},
        -> add_shadow is set from a variable: it must end up false, or the request returns 400.
ERROR  src/cutout.py:11  [format_zip]
        data={"size": "full", "format": "zip", "add_shadow": shadow},
        -> format=zip returns 400 invalid_format. Use png, webp or jpg.
CHECK  src/cutout.py:11  [size_large]
        data={"size": "full", "format": "zip", "add_shadow": shadow},
        -> Full-size output is capped at 25 megapixels (remove.bg allowed 50); larger images come back scaled to 25 MP.
CHECK  src/cutout.py:14  [x_type]
        return resp.content, resp.headers["X-Type"]
        -> The X-Type response header (foreground category) is not sent by ClearBG. Give it a default where you read it.

1 change, 2 error, 2 check  (use -v to show info)
```

No dependencies, Python 3.9+. It reads Python, JavaScript/TypeScript, PHP, Ruby, Go, Java, C#, shell scripts, config files and more as plain text, so it works on any codebase.

## Install

```bash
pip install git+https://github.com/OWNER/removebg-migrate
```

Or clone it and run `python -m removebg_migrate`.

## Usage

### 1. Scan

```bash
removebg-migrate scan path/to/project        # changes, errors and checks
removebg-migrate scan path/to/project -v     # plus informational notes
removebg-migrate scan . --json               # machine-readable
removebg-migrate scan . --strict             # exit 1 on any error-level finding, for CI
```

Parameter checks only run on files that mention remove.bg, so `position: absolute` in your CSS is left alone. Values set from variables are reported with what they need to be, since the scanner can't know them.

### 2. Rewrite the host

```bash
removebg-migrate rewrite path/to/project                          # dry run: prints a diff
removebg-migrate rewrite path/to/project --write                  # apply, default host api.clearbg.org
removebg-migrate rewrite path/to/project --to api.example.com --write
```

Only `api.remove.bg` is replaced. Your API key lives in your environment or secrets store, so change it there.

### 3. Try one image

```bash
BG_API_KEY=... removebg-migrate try photo.jpg                 # size=preview
BG_API_KEY=... removebg-migrate try photo.jpg --size full -o out.png
```

It prints the result size, `X-Credits-Charged`, the rate-limit headers and whether `X-Type` was sent. On ClearBG, preview calls are free (50 a month); on remove.bg a preview costs 0.25 credits.

## What changes

These are the differences between remove.bg's v1.0 API and the [remove.bg-compatible API](https://clearbg.org/background-removal-api) at `api.clearbg.org`, which is what the scanner checks for. Other compatible services make similar choices, but check their documentation.

| Area | remove.bg | api.clearbg.org | Scanner rule |
|---|---|---|---|
| Host | `api.remove.bg` | `api.clearbg.org`, same `/v1.0/removebg` path | `host` |
| Auth | `X-Api-Key` or OAuth | `X-Api-Key` only | `oauth` |
| `/v1.0/improve` | available | 404 | `improve` |
| Input | 22 MB, 50 MP | JPG, PNG, WebP; 25 MB; 12,000 px per side | |
| `size` | default `preview`; `full`/`4k`/`auto`/`50MP` up to 50 MP | default `preview` (same); full sizes capped at 25 MP | `size_large` |
| `format` | `auto`, `png`, `jpg`, `webp`, `zip` | `zip` returns 400; `jpg` is a real JPEG on `bg_color` or white | `format_zip` |
| `bg_color` | hex incl. 4/8-digit alpha, colour names | 3/6-digit hex, 17 basic CSS names; alpha returns 400 | `bg_color_alpha` |
| `bg_image_url` / `bg_image_file` | background image | 400 `invalid_bg_image_url` | `bg_image` |
| `add_shadow`, `shadow_type` | shadows | 400 `unsupported_shadow` unless false / none | `add_shadow`, `shadow_type` |
| `crop_margin`, `roi`, `scale`, `position` | supported | only 0, full image, `original`, `original`; others 400 | same names |
| `type`, `type_level`, `semitransparency`, `shadow_opacity` | supported | accepted and ignored | `ignored_fields` |
| `X-Type` header | foreground category | not sent | `x_type` |
| `X-Credits-Charged` | 0.25 for a preview | integer: 1 full, 0 preview | `credits_header` |
| Rate limit | 500 megapixel-weighted images/min | 500 requests/min per key; 4 images in progress per account (429 with `Retry-After: 2`) | |
| Errors | `{"errors":[{title, code, detail}]}` | same shape and codes; failed requests are not charged | |

Requests are synchronous on both. A compatible endpoint backed by a GPU may wait for a cold start, so give clients a generous timeout; the examples here use 150 seconds.

## The client

If you'd rather replace your HTTP code than patch it, there is a small standard-library client:

```python
from removebg_migrate import RemoveBgClient, ApiError

client = RemoveBgClient(api_key="...", base_url="https://api.clearbg.org")

result = client.remove_background("photo.jpg", size="full", crop=True)
open("photo.png", "wb").write(result.content)
print(result.width, result.height, result.credits_charged, result.foreground_type)

try:
    client.remove_background(image_url="https://example.com/a.jpg", crop_margin="10%")
except ApiError as e:
    print(e.status, e.code)        # 400 invalid_crop_margin
```

It retries 429 and 503 after the `Retry-After` delay, uses a 150-second timeout, and reads `BG_API_KEY` and `BG_API_BASE` from the environment if you don't pass them. `client.account()` returns the balance without using a credit.

## Examples

[`examples/`](examples) has before/after versions of the same call in [curl](examples/curl.sh), [Python](examples/python_requests.py), [Node.js](examples/node_fetch.mjs) and [PHP](examples/php_curl.php), and [`batch_folder.py`](examples/batch_folder.py), which processes a folder 4 images at a time and skips files that are already done.

## Running the tests

```bash
python -m unittest discover -s tests -v
```

The client tests run against a local HTTP server, so they make no network calls and cost nothing.

## About

This tool is made by the team behind [ClearBG](https://clearbg.org/), an independent background removal service with a remove.bg-compatible API; it is not affiliated with remove.bg, Canva or Leonardo.Ai. The scanner and client work with any endpoint that speaks the remove.bg v1.0 protocol; `--to` and `base_url` take any host. If you are moving the website side as well, the [remove.bg alternative](https://clearbg.org/remove-bg-alternative) page covers the shutdown dates and what changes for web users.

Issues and pull requests are welcome, especially new scanner rules and fixtures from real codebases.

## License

MIT
