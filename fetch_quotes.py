#!/usr/bin/env python
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SYMBOLS = ["SPMO", "DRAM", "NOK", "MU", "NOW", "XMHQ", "QQQ", "SPY", "SMH", "SOXX", "XLV", "XLP", "XLU", "XLE"]
OUT = Path("quotes/latest.json")


def fetch_quote(symbol: str, token: str) -> dict:
    url = "https://finnhub.io/api/v1/quote?" + urllib.parse.urlencode({"symbol": symbol, "token": token})
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    token = os.environ.get("FINNHUB_API_KEY")
    if not token:
        raise SystemExit("FINNHUB_API_KEY is required")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    quotes: dict[str, dict] = {}
    errors: dict[str, str] = {}
    for symbol in SYMBOLS:
        try:
            data = fetch_quote(symbol, token)
            if isinstance(data, dict) and data.get("c"):
                quotes[symbol] = data
            else:
                errors[symbol] = data.get("error", "empty quote") if isinstance(data, dict) else "invalid quote"
        except Exception as exc:  # noqa: BLE001
            errors[symbol] = f"{type(exc).__name__}: {exc}"
        time.sleep(1.1)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "symbols": SYMBOLS,
        "quotes": quotes,
        "errors": errors,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT} quotes={len(quotes)} errors={len(errors)}")


if __name__ == "__main__":
    main()
