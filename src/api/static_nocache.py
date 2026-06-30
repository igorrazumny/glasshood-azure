"""A StaticFiles subclass that forces revalidation for the architecture page's
entrypoint HTML, JS, and CSS.

Why: the architecture page's `index.html`, `app.js`, and `styles.css` are served at
fixed, un-hashed URLs (unlike the main React app's build output, which Vite emits with
content-hashed filenames and can safely rely on normal long-lived caching). `styles.css`
is even manually versioned via a `?v=N` query string in the page's own `<link>` tag — a
human/agent has to remember to bump it on every edit. Without a server-side revalidation
guarantee, a browser that visited the page before a content-only edit (HTML markup
changes, CSS rule changes, JS tweaks) can keep serving the stale cached copy of one file
against a freshly-deployed copy of another, producing a page that looks broken even
though the deployed source is already correct. (This exact failure mode hit
architecture.testrobin.ai on 2026-07-01: a 3-day-stale `styles.css` paired with
same-day-fresh HTML blew up an icon via a leftover sizing rule.)

`Cache-Control: no-cache, must-revalidate` is "revalidate, don't blindly refetch" —
StaticFiles still emits an ETag/Last-Modified, so an unchanged file returns a cheap 304
and a changed file is re-fetched automatically. Images under `architecture/img/` keep
their default caching (they're swapped by filename, not edited in place).

Kept in its own module (not server.py) so it's unit-testable without importing the full
app (server.py pulls in GCP clients, background pollers, etc. at import time).
"""
from starlette.staticfiles import StaticFiles


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        # path is the normalized relative path; "." is the directory root (-> index.html
        # in html mode).
        if path == "." or path.endswith((".html", ".js", ".css")):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response
