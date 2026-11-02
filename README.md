# Athmar Platinum Forecasting

Research-only daily platinum-price forecasts in **USD/kg** through **2027-12-31**. No trained model or verified price forecasts yet.

## Sources
`python -m platinum.acquire --out raw/acquired` collects original World Bank (monthly), WPIC (quarterly) and CFTC (weekly) files with SHA-256 manifests. Monthly World Bank averages **cannot** train a daily model. WPIC and CFTC must be joined by release timestamp (point-in-time) after metric validation.

## Daily price training
Supply actual licensed daily `Date,Close` records as `data/daily/platinum.csv`, with documented vendor, reference instrument (spot or futures), and futures roll method.

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m platinum.acquire --out raw/acquired
python -m platinum.daily --csv data/daily/platinum.csv --instrument NYMEX_PL_CONTINUOUS
```

The workflow `platinum-research.yml` executes tests and acquisition on schedule or manually. Manual `train_daily=true` requires an authenticated price file and repository variable `PLATINUM_INSTRUMENT`. The system **fails closed** when data is missing, never substitutes synthetic observations, and performs no trading.

Daily model predictions are experimental weekday estimates, **not** calibrated market trading-day forecasts. They require out-of-sample tests and exchange calendars, plus audited fundamentals and CFTC positioning, before any deployment. No merge to main or publication without review.
