"""Fetch upstream source files as raw evidence. Fail closed on download errors."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import requests

SOURCES = {
    "world_bank_monthly": "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx",
    "wpic_q2_2026": "https://platinuminvestment.com/files/354715/WPIC_PQ_tables_Q2_2026.xlsx",
    "cftc_2024": "https://www.cftc.gov/files/dea/history/fut_disagg_txt_2024.zip",
    "cftc_2025": "https://www.cftc.gov/files/dea/history/fut_disagg_txt_2025.zip",
    "cftc_2026": "https://www.cftc.gov/files/dea/history/fut_disagg_txt_2026.zip",
}
def fetch_one(name, url, output, client=requests):
    suffix = ".xlsx" if url.endswith(".xlsx") else ".zip"
    result = client.get(url, timeout=60, stream=True)
    result.raise_for_status()
    chunks, total = [], 0
    for part in result.iter_content(chunk_size=131072):
        if not part:
            continue
        total += len(part)
        if total > 100_000_000:
            raise ValueError("Source file exceeds 100 MB limit")
        chunks.append(part)
    data = b"".join(chunks)
    if not data.startswith(b"PK"):
        raise ValueError("Expected an XLSX or ZIP file, not an HTML/error page")
    output.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = output / f"{name}_{timestamp}{suffix}"
    path.write_bytes(data)
    return {"name": name, "source_url": url, "retrieved_at": timestamp,
            "path": str(path), "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": total, "status": "raw_unparsed"}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="raw/acquired")
    args = p.parse_args()
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for name, url in SOURCES.items():
        try:
            results.append(fetch_one(name, url, output))
        except Exception as exc:
            results.append({"name": name, "source_url": url, "status": "failed",
                            "error": str(exc)})
    (output / "manifest.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    if any(item["status"] == "failed" for item in results):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
