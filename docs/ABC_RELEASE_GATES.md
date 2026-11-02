# A → B → C: Status and hard gates

## A — Data
- SQLite tables for prices, published fundamental releases and CFTC COT releases.
- Point-in-time join only uses rows with published_at earlier than the next UTC session boundary.
- **Blocked:** actual WPIC XLSX / CFTC archives have not been parsed into the release tables. Daily futures vendor permissions and continuous roll policy unverified. No claim of finalized institutional database.

## B — Evaluation
- Leakage-aware, chronologically purged final holdout for horizons 1,5,20,60,90 observations.
- Models: Ridge, Random Forest, HistGradientBoosting, and no-change baseline. Comparisons measured on out-of-sample log-return MAE.
- **Blocked:** no multiple temporal folds, uncertainty significance tests, or economic-feature ablation. Model champion is research-only.

## C — Forecast outputs
- Daily weekdays until 2027-12-31, USD/kg. For explicitly trained horizons 1/5/20/60/90 use the chosen direct-horizon estimator.
- All other dates show *last-observed-price baseline*, explicitly labeled rather than fake multi-year AI forecasts.
- **Blocked:** exchange calendar, 2027 supply-demand scenarios, probabilistic intervals, calibrations and external-market validation.
- Nothing trades. No independent approval means no production release or automatically merged code.

## Run
```sh
python -m pip install -r requirements.txt
python -m pytest
python -m platinum.price_source --out raw/daily
python -m platinum.model_competition --csv raw/daily/platinum_daily_futures.csv --instrument YAHOO_PL_F_FUTURES_INDICATIVE
```
