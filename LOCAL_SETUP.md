# Athmar Precious Metals Intelligence - Local Windows Setup

This package contains the current four-metal platform:

- Platinum
- Gold
- Silver
- Palladium

Use the dropdown in the dashboard to switch between them.

## Requirements

- Windows 10/11
- Python 3.11+
- Node.js 22+
- Internet access is required only when you want to refresh market data or reinstall packages.

## Fastest start

Double-click:

`run-local.bat`

Or open PowerShell inside the project folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-local.ps1
```

The launcher will:

1. create `.venv` if needed;
2. install Python requirements;
3. run Platinum + multi-metal safety tests;
4. install Next.js dependencies;
5. start the dashboard.

Open:

`http://localhost:3000`

The included `web/data/metals-state.json` already contains the latest checked-in Shadow state, so the dashboard can be tested immediately.

## Manual dashboard start

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd web
npm install
npm run dev
```

Then open:

`http://localhost:3000`

## Refresh Gold, Silver and Palladium locally

Activate Python:

```powershell
.\.venv\Scripts\Activate.ps1
```

Generate new locked Shadow forecasts for the three new metals:

```powershell
python -m metals.shadow --all
```

Then rebuild the combined four-metal dashboard state:

```powershell
python -m metals.platform_state --out web/data/metals-state.json
```

Restart `npm run dev` if needed.

## Refresh Platinum locally

Acquire the latest Platinum reference futures price and market features:

```powershell
python -m platinum.price_source --out raw/daily
python -m platinum.market_features --out outputs/features/market
python -m platinum.wpic_pit_prepare --input data/verified/platinum_supply_demand_pit_user_extracted.csv --out outputs/features/wpic
python -m platinum.wpic_engineering --input data/verified/platinum_supply_demand_pit_user_extracted.csv --out outputs/features/wpic_engineered
```

Build the locked 90-day Platinum feature map:

```powershell
python -c "import json; from pathlib import Path; m=json.loads(Path('outputs/features/market/feature_paths_market.json').read_text()); l=json.loads(Path('outputs/features/wpic/feature_paths_wpic.json').read_text()); e=json.loads(Path('outputs/features/wpic_engineered/feature_paths_engineered.json').read_text()); Path('outputs/features/shadow_v1_90d.json').write_text(json.dumps({**m,**l,**e},indent=2))"
```

Generate Platinum Shadow forecasts and rebuild its state:

```powershell
python -m platinum.shadow_forecast --daily raw/daily/platinum_daily_futures.csv --features outputs/features/shadow_v1_90d.json --model-lock config/model_lock_v1.json --artifact config/model_artifact_v1_90d.json --journal data/shadow/forecast_journal.csv
python -m platinum.platform_snapshot --price-csv raw/daily/platinum_daily_futures.csv --journal-csv data/shadow/forecast_journal.csv --out web/data/live-state.json
python -m metals.platform_state --out web/data/metals-state.json
```

## Safety

- Each metal has an independent V1 lock.
- Prospective holdout outcomes are not scored by the local Shadow commands.
- Platinum keeps its existing WPIC point-in-time system.
- Gold, Silver and Palladium V1 do not claim official fundamentals.
- No automated trading is included.
