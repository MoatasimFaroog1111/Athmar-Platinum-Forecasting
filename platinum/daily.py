"""Experimental daily USD/kg model, not production trading signals."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error

OZ_PER_KG = 32.1507465686
LAGS = 20

def load_daily(path):
    source = Path(path)
    if not source.is_file():
        raise ValueError("Verified daily price CSV is missing; training blocked")
    df = pd.read_csv(source)
    if not {"Date", "Close"} <= set(df.columns):
        raise ValueError("Expected Date and Close columns")
    df["Date"] = pd.to_datetime(df["Date"], errors="raise", utc=True)
    df["Close"] = pd.to_numeric(df["Close"], errors="raise")
    df = df.sort_values("Date")
    if df.Date.duplicated().any() or df.Close.isna().any() or (df.Close <= 0).any():
        raise ValueError("Invalid, duplicate, missing or nonpositive daily prices")
    if len(df) < 280:
        raise ValueError("Require >=280 distinct daily price observations")
    if (df.Date.dt.dayofweek >= 5).any():
        raise ValueError("Weekends detected; confirm actual daily trading sessions")
    return df.reset_index(drop=True)

def features(log_prices):
    returns = np.diff(log_prices)
    x, y = [], []
    for idx in range(LAGS, len(returns)):
        x.append(returns[idx-LAGS:idx])
        y.append(returns[idx])
    return np.asarray(x), np.asarray(y)

def fit_and_forecast(csv, instrument, output="outputs/daily", unit="USD/troy_oz"):
    if not instrument.strip():
        raise ValueError("Source instrument identity is required")
    df = load_daily(csv)
    prices = df.Close.to_numpy(dtype=float)
    if unit == "USD/troy_oz":
        prices *= OZ_PER_KG
    elif unit != "USD/kg":
        raise ValueError("Unsupported unit")
    x, y = features(np.log(prices))
    if len(y) < 100:
        raise ValueError("Insufficient aligned samples")
    split = int(len(y) * 0.8)
    predictions = []
    baseline = []
    for i in range(split, len(y)):
        model = Ridge(alpha=1.0).fit(x[:i], y[:i])
        predictions.append(model.predict(x[i:i+1])[0])
        baseline.append(0.0)
    metrics = {"instrument": instrument, "unit": "USD/kg", "observations": len(df),
        "test_observations": len(predictions), "test_return_mae": float(mean_absolute_error(y[split:], predictions)),
        "no_change_return_mae": float(mean_absolute_error(y[split:], baseline)),
        "last_actual_date": df.Date.iloc[-1].date().isoformat(),
        "model_status": "experimental_not_validated"}
    model = Ridge(alpha=1.0).fit(x, y)
    future_dates = pd.bdate_range(start=df.Date.iloc[-1] + pd.Timedelta(days=1), end="2027-12-31")
    rolling_returns = list(np.diff(np.log(prices))[-LAGS:])
    estimate = float(prices[-1])
    rows = []
    for day in future_dates:
        next_ret = float(model.predict(np.asarray(rolling_returns[-LAGS:]).reshape(1, -1))[0])
        estimate *= float(np.exp(next_ret))
        rolling_returns.append(next_ret)
        rows.append({"target_date": day.date().isoformat(), "forecast_usd_kg": estimate,
                     "reference_instrument": instrument, "status": "experimental"})
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "backtest.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    pd.DataFrame(rows, columns=["target_date","forecast_usd_kg","reference_instrument","status"]).to_csv(
        out / "forecasts_experimental.csv", index=False)
    return metrics

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--instrument", required=True)
    p.add_argument("--unit", default="USD/troy_oz", choices=["USD/troy_oz", "USD/kg"])
    p.add_argument("--output", default="outputs/daily")
    args = p.parse_args()
    print(json.dumps(fit_and_forecast(args.csv, args.instrument, args.output, args.unit), indent=2))

if __name__ == "__main__":
    main()
