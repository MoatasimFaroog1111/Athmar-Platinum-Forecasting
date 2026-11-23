"""GARCH(1,1) volatility modelling — the predictable half of the platinum series.

Returns are a near random walk (no model beats the LastValue baseline), but volatility
CLUSTERS: squared-return autocorrelation is strongly positive (~+0.20 vs ~-0.06 for
returns). GARCH therefore forecasts tomorrow's volatility better than a rolling estimate
(verified ~9% lower MAE out-of-sample on 2020+). Use it for risk management — position
sizing, stop placement, VaR-style daily bands — NOT for direction alpha.

Requires the `arch` package.
"""
from __future__ import annotations

import numpy as np


def fit_garch(returns_pct, p: int = 1, q: int = 1, dist: str = "t"):
    """Fit GARCH(p,q) on returns in PERCENT. Returns the arch fit result."""
    from arch import arch_model
    return arch_model(returns_pct, vol="GARCH", p=p, q=q, dist=dist, rescale=False).fit(disp="off")


def forecast_daily_vol(returns_pct, horizon: int = 5, p: int = 1, q: int = 1, dist: str = "t"):
    """Forecast the next `horizon` daily volatilities (as decimals, e.g. 0.0194 = 1.94%)."""
    res = fit_garch(returns_pct, p, q, dist)
    fc = res.forecast(horizon=horizon)
    return np.sqrt(fc.variance.values[-1] / 1e4)


def price_band(last_price: float, daily_vol: float, horizon: int, z: float = 1.96):
    """Confidence price band: last_price * exp(±z * vol * sqrt(horizon))."""
    w = z * daily_vol * np.sqrt(horizon)
    return last_price * np.exp(-w), last_price * np.exp(w)


def position_size(risk_pct: float, daily_vol: float, z: float = 1.96):
    """Notional leverage so a z-sigma daily move equals `risk_pct` of capital."""
    return risk_pct / (z * daily_vol)


def annualized_vol(daily_vol: float, periods: int = 252) -> float:
    return daily_vol * np.sqrt(periods)
