import base64
import binascii
import hmac
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
PASSWORD = os.environ.get("ESRA_SITE_PASSWORD", "")
PORT = 8787

if len(PASSWORD) < 16:
    raise SystemExit("Set ESRA_SITE_PASSWORD to a unique password of at least 16 characters.")

PHOTO_NAMES = (
    "guzel-anilarimiz-01.png",
    "ani-02-portre.png",
    "ani-03-park.png",
    "ani-04-aksam.png",
    "ani-05-birlikte.png",
    "ani-06-anilarimiz.jpg",
    "ani-07-anilarimiz.jpg",
    "ani-08-kedicikle.png",
    "ani-09-dogum-gunu.png",
    "ani-10-kafede.png",
    "ani-11-anilarimiz.jpg",
    "ani-12-birlikte.png",
    "ani-13-aksam.png",
    "ani-14-park.png",
    "ani-15-bizden.png",
)

FILES = {
    "/": ROOT / "index.html",
    "/index.html": ROOT / "index.html",
    "/mutluluklar.html": ROOT / "mutluluklar.html",
    "/mektup.html": ROOT / "mektup.html",
    "/styles.css": ROOT / "styles.css",
    "/script.js": ROOT / "script.js",
    "/videos/esra-icin-montaj.mp4": ROOT / "videos" / "esra-icin-montaj.mp4",
}
FILES.update({f"/photos/{name}": ROOT / "photos" / name for name in PHOTO_NAMES})

CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".jpg": "image/jpeg",
    ".mp4": "video/mp4",
    ".png": "image/png",
}


class PrivateSiteHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "PrivateMemorySite"
    sys_version = ""

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self'; media-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Robots-Tag", "noindex, nofollow, noarchive")
        super().end_headers()

    def is_authorized(self):
        value = self.headers.get("Authorization", "")
        scheme, separator, encoded = value.partition(" ")
        if not separator or scheme.lower() != "basic":
            return False

        try:
            credentials = base64.b64decode(encoded, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return False

        username, separator, supplied_password = credentials.partition(":")
        return (
            separator == ":"
            and username == "esra"
            and hmac.compare_digest(supplied_password, PASSWORD)
        )

    def authenticate(self):
        if self.is_authorized():
            return True

        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Private Site", charset="UTF-8"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def send_file(self, head_only):
        if not self.authenticate():
            return

        path = urlsplit(self.path).path
        file_path = FILES.get(path)
        if file_path is None:
            self.send_error(404)
            return

        try:
            file_size = file_path.stat().st_size
        except FileNotFoundError:
            self.send_error(404)
            return

        start = 0
        end = file_size - 1
        status = 200
        range_header = self.headers.get("Range")

        if range_header:
            byte_range = self.parse_range(range_header, file_size)
            if byte_range is None:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{file_size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            start, end = byte_range
            status = 206

        content_length = max(0, end - start + 1)
        self.send_response(status)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Type", CONTENT_TYPES.get(file_path.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(content_length))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.end_headers()

        if head_only:
            return

        with file_path.open("rb") as file:
            file.seek(start)
            remaining = content_length
            while remaining:
                chunk = file.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    @staticmethod
    def parse_range(value, file_size):
        if not value.startswith("bytes=") or "," in value or file_size == 0:
            return None

        first, separator, last = value[6:].partition("-")
        if not separator:
            return None

        try:
            if not first:
                suffix_length = int(last)
                if suffix_length <= 0:
                    return None
                start = max(file_size - suffix_length, 0)
                end = file_size - 1
            else:
                start = int(first)
                end = int(last) if last else file_size - 1
        except ValueError:
            return None

        if start < 0 or end < start or start >= file_size:
            return None
        return start, min(end, file_size - 1)

    def do_GET(self):
        self.send_file(head_only=False)

    def do_HEAD(self):
        self.send_file(head_only=True)

    def do_POST(self):
        self.send_error(405)

    def do_PUT(self):
        self.send_error(405)

    def do_DELETE(self):
        self.send_error(405)


def main():
    mimetypes.init()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), PrivateSiteHandler)
    server.daemon_threads = True
    print(f"Password-protected site origin listening on http://127.0.0.1:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
