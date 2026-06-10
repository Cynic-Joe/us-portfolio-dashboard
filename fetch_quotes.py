#!/usr/bin/env python
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SYMBOLS = ["SPMO", "DRAM", "NOK", "MU", "NOW", "QQQ", "SPY", "SMH", "SOXX", "XLV", "XLP", "XLU", "XLE"]
MARKET_SYMBOLS = ["^VIX", "SOXX", "UUP"]  # VIX, semiconductor proxy, dollar ETF proxy
OUT = Path("quotes/latest.json")
FOREX_OUT = Path("quotes/latest.json")  # merged into same file


def fetch_quote(symbol: str, token: str) -> dict:
    url = "https://finnhub.io/api/v1/quote?" + urllib.parse.urlencode({"symbol": symbol, "token": token})
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_forex_rates() -> dict:
    """Fetch exchange rates from frankfurter.app (ECB data, free, no CORS/key needed)."""
    try:
        url = "https://api.frankfurter.app/latest?from=USD&to=CNY,HKD"
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            rates = data.get("rates", {})
            return {
                "USDCNY": rates.get("CNY"),
                "USDHKD": rates.get("HKD"),
                "date": data.get("date"),
            }
    except Exception as exc:
        print(f"forex fetch failed: {exc}")
        # Fallback to exchangerate-api
        try:
            url2 = "https://open.er-api.com/v6/latest/USD"
            with urllib.request.urlopen(url2, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))
                rates = data.get("rates", {})
                return {
                    "USDCNY": rates.get("CNY"),
                    "USDHKD": rates.get("HKD"),
                    "date": data.get("time_last_update_utc", ""),
                }
        except Exception as exc2:
            print(f"forex fallback also failed: {exc2}")
            return {}


def fetch_treasury_yield() -> float | None:
    """Fetch 10Y Treasury yield from Finnhub treasury endpoint."""
    token = os.environ.get("FINNHUB_API_KEY")
    if not token:
        return None
    try:
        # Use the treasury yield curve endpoint
        url = "https://finnhub.io/api/v1/treasury-yield?" + urllib.parse.urlencode({
            "token": token,
            "freq": "daily",
        })
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            # data is an array of {date, value} for different maturities
            # Look for 10-year
            if isinstance(data, list):
                for entry in data:
                    if entry.get("maturity") == "10y" or entry.get("label") == "10Y":
                        return entry.get("value")
    except Exception:
        pass
    return None


def main() -> None:
    token = os.environ.get("FINNHUB_API_KEY")
    if not token:
        raise SystemExit("FINNHUB_API_KEY is required")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    quotes: dict[str, dict] = {}
    errors: dict[str, str] = {}
    all_symbols = SYMBOLS + MARKET_SYMBOLS
    for symbol in all_symbols:
        try:
            data = fetch_quote(symbol, token)
            if isinstance(data, dict) and data.get("c"):
                quotes[symbol] = data
            else:
                errors[symbol] = data.get("error", "empty quote") if isinstance(data, dict) else "invalid quote"
        except Exception as exc:  # noqa: BLE001
            errors[symbol] = f"{type(exc).__name__}: {exc}"
        time.sleep(1.1)

    # Fetch forex rates
    forex = fetch_forex_rates()

    # Fetch 10Y yield
    yield_10y = fetch_treasury_yield()
    market_data = {
        "USDCNY": forex.get("USDCNY"),
        "USDHKD": forex.get("USDHKD"),
        "forex_date": forex.get("date"),
        "yield10y": yield_10y,
    }

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "symbols": all_symbols,
        "quotes": quotes,
        "errors": errors,
        "market": market_data,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT} quotes={len(quotes)} errors={len(errors)} forex={bool(forex)} yield={yield_10y}")


if __name__ == "__main__":
    main()
