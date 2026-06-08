#!/usr/bin/env python
"""Local server for Jake's US portfolio dashboard.

Serves us-portfolio-dashboard.html and proxies Finnhub quote requests using
FINNHUB_API_KEY from Hermes .env, so the API key is not embedded in the page.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / "AppData" / "Local" / "hermes" / ".env"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


class Handler(SimpleHTTPRequestHandler):
    def end_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/quotes":
            self.handle_quotes(parsed)
            return
        if parsed.path in {"/", ""}:
            self.path = "/us-portfolio-dashboard.html"
        return super().do_GET()

    def handle_quotes(self, parsed) -> None:
        token = os.environ.get("FINNHUB_API_KEY")
        if not token:
            self.end_json(500, {"error": "FINNHUB_API_KEY not found in environment or Hermes .env"})
            return
        query = urllib.parse.parse_qs(parsed.query)
        symbols = [s.strip().upper() for s in query.get("symbols", [""])[0].split(",") if s.strip()]
        if not symbols:
            self.end_json(400, {"error": "symbols query parameter required"})
            return
        quotes: dict[str, dict] = {}
        errors: dict[str, str] = {}
        for symbol in symbols:
            url = "https://finnhub.io/api/v1/quote?" + urllib.parse.urlencode({"symbol": symbol, "token": token})
            try:
                with urllib.request.urlopen(url, timeout=12) as response:
                    data = json.loads(response.read().decode("utf-8"))
                if isinstance(data, dict) and data.get("c"):
                    quotes[symbol] = data
                else:
                    errors[symbol] = data.get("error", "empty quote") if isinstance(data, dict) else "invalid quote"
            except Exception as exc:  # noqa: BLE001
                errors[symbol] = f"{type(exc).__name__}: {exc}"
        self.end_json(200, {"quotes": quotes, "errors": errors})


def main() -> None:
    load_env(ENV_PATH)
    os.chdir(ROOT)
    port = int(os.environ.get("PORT", "8766"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Dashboard: http://127.0.0.1:{port}/us-portfolio-dashboard.html")
    server.serve_forever()


if __name__ == "__main__":
    main()
