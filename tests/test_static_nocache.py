"""Tests for src.api.static_nocache.NoCacheStaticFiles.

Driven via a tiny throwaway Starlette app + TestClient against a temp directory —
src.api.server is NOT imported (it pulls in GCP clients and background pollers at
import time). Mirrors TestRobin's backend/tests/test_static_nocache.py.
"""
from starlette.applications import Starlette
from starlette.testclient import TestClient

from src.api.static_nocache import NoCacheStaticFiles


def _client(tmp_path):
    (tmp_path / "index.html").write_text("<title>ARCH</title>")
    (tmp_path / "styles.css").write_text("body{color:red}")
    (tmp_path / "app.js").write_text("console.log('x')")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n")
    app = Starlette()
    app.mount("/architecture", NoCacheStaticFiles(directory=str(tmp_path), html=True))
    return TestClient(app)


def test_entrypoint_html_is_no_cache(tmp_path):
    c = _client(tmp_path)
    r = c.get("/architecture/")
    assert r.status_code == 200
    assert "no-cache" in r.headers.get("cache-control", "")


def test_css_is_no_cache(tmp_path):
    """The architecture page's manually `?v=N`-versioned styles.css must revalidate on
    every load — a stale-cached copy bit architecture.testrobin.ai production on
    2026-07-01 (old sizing rule + new markup -> a blown-up icon)."""
    c = _client(tmp_path)
    r = c.get("/architecture/styles.css")
    assert r.status_code == 200
    assert "no-cache" in r.headers.get("cache-control", "")


def test_js_is_no_cache(tmp_path):
    c = _client(tmp_path)
    r = c.get("/architecture/app.js")
    assert r.status_code == 200
    assert "no-cache" in r.headers.get("cache-control", "")


def test_image_asset_keeps_default_caching(tmp_path):
    c = _client(tmp_path)
    r = c.get("/architecture/logo.png")
    assert r.status_code == 200
    assert "no-cache" not in r.headers.get("cache-control", "")


def test_etag_revalidation_still_works(tmp_path):
    """no-cache means revalidate, not refetch — an unchanged file still returns a cheap
    304 on a conditional request."""
    c = _client(tmp_path)
    first = c.get("/architecture/styles.css")
    etag = first.headers["etag"]
    second = c.get("/architecture/styles.css", headers={"if-none-match": etag})
    assert second.status_code == 304
