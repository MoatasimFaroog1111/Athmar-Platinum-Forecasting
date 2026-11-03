"""Research-only acquisition of Yahoo PL=F daily futures chart bars.

Unofficial endpoint. Usage and redistribution need independent legal review.
This is a futures chart, NOT a platinum spot benchmark. Never silently backfill
or mix an unadjusted contract roll with a spot series.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

URL = "https://query1.finance.yahoo.com/v8/finance/chart/PL=F"
OZ_PER_KG = 32.1507465686


def parse_chart(payload):
    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise ValueError(f"Vendor reported error: {chart['error']}")
    result = chart.get("result")
    if not result or len(result) != 1:
        raise ValueError("No unique Yahoo price chart")
    entry = result[0]
    meta = entry.get("meta") or {}
    currency = meta.get("currency")
    if currency != "USD":
        raise ValueError(f"Expected USD, got {currency!r}")
    quote = (entry.get("indicators") or {}).get("quote") or []
    timestamps = entry.get("timestamp") or []
    if len(quote) != 1 or len(timestamps) != len(quote[0].get("close") or []):
        raise ValueError("Malformed daily price data")
    closes = quote[0]["close"]
    bars = []
    for t, c in zip(timestamps, closes):
        if c is None:
            continue
        value = float(c)
        if not (value > 0 and value < 1_000_000):
            raise ValueError("Invalid nonpositive/out-of-range daily price")
        day = datetime.fromtimestamp(int(t), tz=timezone.utc).date().isoformat()
        bars.append((day, value))
    frame = pd.DataFrame(bars, columns=["Date", "Close"])
    if frame.empty:
        raise ValueError("No valid daily observations")
    if frame.Date.duplicated().any():
        raise ValueError("Duplicate date; intraday timestamps cannot be used as daily bars")
    if not frame.Date.is_monotonic_increasing:
        raise ValueError("Bars not chronologically ordered")
    if len(frame) < 280:
        raise ValueError("Not enough actual daily bars for model training")
    return frame


def fetch_prices(out="raw/daily", session=requests):
    response = session.get(
        URL,
        params={"range": "5y", "interval": "1d"},
        headers={"User-Agent": "Mozilla/5.0 (compatible; Athmar-Platinum-Research/0.4)"},
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    frame = parse_chart(payload)
    base = Path(out)
    base.mkdir(parents=True, exist_ok=True)
    raw = response.content
    (base / "vendor_response.json").write_bytes(raw)
    frame.to_csv(base / "platinum_daily_futures.csv", index=False)
    manifest = {
        "instrument": "Yahoo Finance PL=F (platinum futures indicative chart)",
        "price_unit": "USD/troy_oz",
        "target_price_unit": "USD/kg",
        "oz_troy_per_kg": OZ_PER_KG,
        "source": URL,
        "query": "range=5y&interval=1d",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "row_count": len(frame),
        "first_date": frame.Date.iloc[0],
        "last_date": frame.Date.iloc[-1],
        "status": "research_only_unlicensed_unverified_roll",
        "warning": "Not spot; confirm vendor terms, contract roll and observed data quality before production.",
    }
    (base / "provenance.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="raw/daily")
    args = p.parse_args()
    print(json.dumps(fetch_prices(args.out), indent=2))


if __name__ == "__main__":
    main()
