import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from removebg_migrate.client import ApiError, RemoveBgClient


class Handler(BaseHTTPRequestHandler):
    script = []
    seen = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        Handler.seen.append((self.path, self.headers.get("X-Api-Key"), body))
        status, headers, payload = Handler.script.pop(0)
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST


class ClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        fd, cls.image = tempfile.mkstemp(suffix=".png")
        os.write(fd, b"\x89PNG fake")
        os.close(fd)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        os.remove(cls.image)

    def setUp(self):
        Handler.script, Handler.seen = [], []
        self.sleeps = []
        self.client = RemoveBgClient("k123", base_url=self.base, sleep=self.sleeps.append)

    def test_success_and_headers(self):
        Handler.script = [(200, {"Content-Type": "image/png", "X-Credits-Charged": "1", "X-Width": "640", "X-Height": "480"}, b"PNGDATA")]
        r = self.client.remove_background(self.image, size="full", crop=True)
        self.assertEqual(r.content, b"PNGDATA")
        self.assertEqual((r.width, r.height, r.credits_charged), (640, 480, 1.0))
        self.assertEqual(r.foreground_type, "unknown")
        path, key, body = Handler.seen[0]
        self.assertEqual((path, key), ("/v1.0/removebg", "k123"))
        self.assertIn(b'name="crop"\r\n\r\ntrue', body)
        self.assertIn(b'name="image_file"; filename=', body)

    def test_retries_429_using_retry_after(self):
        busy = json.dumps({"errors": [{"title": "Rate limit exceeded", "code": "rate_limit_exceeded"}]}).encode()
        Handler.script = [(429, {"Retry-After": "2"}, busy), (200, {}, b"OK")]
        r = self.client.remove_background(image_url="https://example.com/a.jpg")
        self.assertEqual(r.content, b"OK")
        self.assertEqual(self.sleeps, [2.0])

    def test_error_shape(self):
        err = json.dumps({"errors": [{"title": "Invalid crop_margin", "code": "invalid_crop_margin"}]}).encode()
        Handler.script = [(400, {}, err)]
        with self.assertRaises(ApiError) as cm:
            self.client.remove_background(self.image, crop_margin="10%")
        self.assertEqual((cm.exception.status, cm.exception.code), (400, "invalid_crop_margin"))

    def test_one_source_only(self):
        with self.assertRaises(ValueError):
            self.client.remove_background()


if __name__ == "__main__":
    unittest.main()
