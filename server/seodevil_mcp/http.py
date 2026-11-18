"""Small HTTP client on top of urllib (no third-party dependencies).

Records every redirect hop, decompresses gzip/deflate, detects the charset
and caps the body size so a huge file can't exhaust memory.
"""
from __future__ import annotations

import gzip
import os
import re
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional, TypeVar

USER_AGENT = os.environ.get(
    "SEODEVIL_USER_AGENT",
    "Mozilla/5.0 (compatible; SEODevil/1.0; +https://github.com/sajidali12/seodevil-plugin)",
)
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
)
MAX_BYTES = 6 * 1024 * 1024
REDIRECT_CODES = {301, 302, 303, 307, 308}


@dataclass
class Response:
    url: str
    final_url: str
    status: int = 0
    headers: dict = field(default_factory=dict)
    body: bytes = b""
    text: str = ""
    elapsed_ms: int = 0
    redirects: list = field(default_factory=list)
    error: Optional[str] = None
    truncated: bool = False

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "").split(";")[0].strip().lower()

    @property
    def is_html(self) -> bool:
        ct = self.content_type
        return ct in ("text/html", "application/xhtml+xml") or (not ct and self.text.lstrip()[:15].lower().startswith(("<!doctype", "<html")))

    def summary(self) -> dict:
        return {
            "url": self.url,
            "final_url": self.final_url,
            "status": self.status,
            "elapsed_ms": self.elapsed_ms,
            "redirects": self.redirects,
            "error": self.error,
        }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


_ctx = ssl.create_default_context()
_opener = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=_ctx))
_cache: dict = {}
_cache_lock = threading.Lock()
CACHE_TTL = 120


def normalize_input_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise ValueError("A URL is required")
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = "https://" + url
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"Only http(s) URLs are supported, got {parts.scheme!r}")
    if not parts.netloc:
        raise ValueError(f"Invalid URL: {url!r}")
    path = parts.path or "/"
    # Percent-encode spaces and other unsafe characters but keep existing escapes.
    path = urllib.parse.quote(path, safe="/%:@!$&'()*+,;=-._~")
    query = urllib.parse.quote(parts.query, safe="=&%:@!$'()*+,;/?-._~")
    return urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def _decode_body(raw: bytes, headers: dict) -> bytes:
    enc = headers.get("content-encoding", "").lower()
    try:
        if "gzip" in enc or raw[:2] == b"\x1f\x8b":
            return gzip.decompress(raw)
        if "deflate" in enc:
            try:
                return zlib.decompress(raw)
            except zlib.error:
                return zlib.decompress(raw, -zlib.MAX_WBITS)
    except (OSError, zlib.error, EOFError):
        return raw
    return raw


def _charset(body: bytes, headers: dict) -> str:
    m = re.search(r"charset=([\w-]+)", headers.get("content-type", ""), re.I)
    if m:
        return m.group(1)
    m = re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", body[:4096], re.I)
    if m:
        return m.group(1).decode("ascii", "ignore")
    return "utf-8"


def _headers_dict(msg) -> dict:
    out: dict = {}
    if msg is None:
        return out
    for k, v in msg.items():
        k = k.lower()
        out[k] = f"{out[k]}, {v}" if k in out else v
    return out


def _one_request(url: str, method: str, timeout: float, ua: str, extra_headers: Optional[dict], max_bytes: int):
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, method=method, headers=headers)
    try:
        resp = _opener.open(req, timeout=timeout)
        status = resp.status
    except urllib.error.HTTPError as e:  # 3xx (no auto-redirect), 4xx, 5xx
        resp = e
        status = e.code
    hdrs = _headers_dict(resp.headers)
    raw = b""
    truncated = False
    if method != "HEAD":
        try:
            raw = resp.read(max_bytes + 1)
        except Exception:  # body read errors on error pages are common; keep what we have
            raw = b""
        if len(raw) > max_bytes:
            raw, truncated = raw[:max_bytes], True
    try:
        resp.close()
    except Exception:
        pass
    return status, hdrs, raw, truncated


def fetch(
    url: str,
    method: str = "GET",
    timeout: float = 20,
    follow: bool = True,
    max_redirects: int = 10,
    ua: Optional[str] = None,
    headers: Optional[dict] = None,
    max_bytes: int = MAX_BYTES,
    use_cache: bool = True,
) -> Response:
    """Fetch a URL, following redirects manually so every hop is recorded."""
    try:
        url = normalize_input_url(url)
    except ValueError as e:
        return Response(url=url, final_url=url, error=str(e))
    ua = ua or USER_AGENT
    key = (url, method, ua, follow, repr(sorted((headers or {}).items())))
    if use_cache and method == "GET":
        with _cache_lock:
            hit = _cache.get(key)
            if hit and time.time() - hit[0] < CACHE_TTL:
                return hit[1]

    start = time.monotonic()
    current = url
    hops: list = []
    seen = {url}
    res = Response(url=url, final_url=url)
    for _ in range(max_redirects + 1):
        try:
            status, hdrs, raw, truncated = _one_request(current, method, timeout, ua, headers, max_bytes)
        except urllib.error.URLError as e:
            reason = e.reason
            if isinstance(reason, ssl.SSLError):
                res.error = f"SSL error: {reason}"
            elif isinstance(reason, socket.gaierror):
                res.error = f"DNS lookup failed for {urllib.parse.urlsplit(current).hostname}"
            else:
                res.error = f"Connection failed: {reason}"
            break
        except (socket.timeout, TimeoutError):
            res.error = f"Timed out after {timeout:g}s"
            break
        except (ssl.SSLError, ssl.CertificateError) as e:
            res.error = f"SSL error: {e}"
            break
        except Exception as e:  # pragma: no cover - defensive
            res.error = f"{type(e).__name__}: {e}"
            break

        res.status, res.headers, res.truncated = status, hdrs, truncated
        res.final_url = current
        loc = hdrs.get("location")
        if follow and status in REDIRECT_CODES and loc:
            nxt = urllib.parse.urljoin(current, loc.strip())
            hops.append({"url": current, "status": status, "location": nxt})
            if nxt in seen:
                res.error = f"Redirect loop detected at {nxt}"
                break
            seen.add(nxt)
            current = nxt
            if status == 303:
                method = "GET" if method != "HEAD" else method
            continue
        body = _decode_body(raw, hdrs)
        res.body = body
        res.text = body.decode(_charset(body, hdrs), errors="replace") if body else ""
        break
    else:
        res.error = f"Too many redirects (>{max_redirects})"

    res.redirects = hops
    res.elapsed_ms = int((time.monotonic() - start) * 1000)
    if use_cache and method == "GET" and not res.error:
        with _cache_lock:
            if len(_cache) > 2000:
                _cache.clear()
            _cache[key] = (time.time(), res)
    return res


def check_status(url: str, timeout: float = 12) -> Response:
    """Cheap status check: HEAD first, GET when the server dislikes HEAD."""
    r = fetch(url, method="HEAD", timeout=timeout, use_cache=False)
    if r.error or r.status in (400, 403, 405, 406, 429, 500, 501, 503) or r.status == 0:
        g = fetch(url, method="GET", timeout=timeout, max_bytes=65536)
        if not g.error or r.error:
            return g
    return r


T = TypeVar("T")
R = TypeVar("R")


def pmap(fn: Callable[[T], R], items: Iterable[T], workers: int = 6) -> List[R]:
    items = list(items)
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(items)))) as ex:
        return list(ex.map(fn, items))


def origin(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    return f"{p.scheme}://{p.netloc}"


def strip_www(host: str) -> str:
    host = (host or "").lower()
    return host[4:] if host.startswith("www.") else host


def same_site(a: str, b: str) -> bool:
    return strip_www(urllib.parse.urlsplit(a).hostname or "") == strip_www(urllib.parse.urlsplit(b).hostname or "")
