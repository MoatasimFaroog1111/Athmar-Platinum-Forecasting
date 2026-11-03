# Athmar Platinum Intelligence — Local Windows Setup

This package is the same project currently used for the Shadow Production platform.

## Requirements
- Windows 10/11
- Python 3.11+
- Node.js 22+
- Git is optional

## Fastest start — dashboard only

Double-click:

`run-local.bat`

or open PowerShell in the project folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-local.ps1
```

The script:
1. creates `.venv` if missing;
2. installs Python requirements;
3. installs web dependencies;
4. runs the safety tests;
5. starts the dashboard at http://localhost:3000.

The dashboard uses the checked-in live Shadow state and does not need cloud credentials.

## Refresh the market snapshot locally

Activate the Python environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then:

```powershell
python -m platinum.price_source --out raw/daily
python -m platinum.market_features --out outputs/features/market
python -m platinum.wpic_pit_prepare --input data/verified/platinum_supply_demand_pit_user_extracted.csv --out outputs/features/wpic
python -m platinum.wpic_engineering --input data/verified/platinum_supply_demand_pit_user_extracted.csv --out outputs/features/wpic_engineered
```

Build the locked 90-day feature map:

```powershell
python -c "import json; from pathlib import Path; m=json.loads(Path('outputs/features/market/feature_paths_market.json').read_text()); l=json.loads(Path('outputs/features/wpic/feature_paths_wpic.json').read_text()); e=json.loads(Path('outputs/features/wpic_engineered/feature_paths_engineered.json').read_text()); Path('outputs/features/shadow_v1_90d.json').write_text(json.dumps({**m,**l,**e},indent=2))"
```

Generate a local Shadow record (no holdout scoring):

```powershell
python -m platinum.shadow_forecast --daily raw/daily/platinum_daily_futures.csv --features outputs/features/shadow_v1_90d.json --model-lock config/model_lock_v1.json --artifact config/model_artifact_v1_90d.json --journal data/shadow/forecast_journal.csv
python -m platinum.platform_snapshot --price-csv raw/daily/platinum_daily_futures.csv --journal-csv data/shadow/forecast_journal.csv --out web/data/live-state.json
```

Restart the web app to see the refreshed state.

## Safety
- V1 model/protocol files are locked.
- Local runs must not score prospective holdout outcomes before the protocol unlock.
- The dashboard is read-only.
- No automated trading is included.
