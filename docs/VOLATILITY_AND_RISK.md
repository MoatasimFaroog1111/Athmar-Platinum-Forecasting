# Volatility & Risk — Research Findings (2026-11)

Complements the existing point-in-time and walk-forward work with the two results that
make the system *usable*: volatility is predictable, and fundamental balance is not.

## 1. Returns are random, volatility is predictable

Statistical diagnosis of daily platinum log-returns (1997–2026):

| Measure | Value | Meaning |
|---|---|---|
| AC(return, lag1) | −0.062 | ~no serial correlation |
| AC(return², lag1) | **+0.200** | volatility clusters → predictable |
| AR(1) R² | 0.38% | yesterday explains <0.5% of tomorrow |
| signal/noise | 0.16 | noise is ~6× the signal |
| kurtosis | +166 | fat tails (crisis jumps) |

**GARCH(1,1)-t** fit: α≈0.047, β≈0.913 (persistence ≈0.96), ν≈4.6 (student-t). Out-of-sample
(2020+) vol forecast vs `|return|`: **GARCH MAE 0.0114 vs rolling-20d-std 0.0125** (~9% better).

## 2. Volatility targeting — the honest application

Scaling position size inversely with forecast vol (target 1.5%/day, walk-forward 2020+):

| Strategy | Ann. ret | Ann. vol | Sharpe | Max drawdown |
|---|---|---|---|---|
| buy & hold | +5.8% | 36.9% | 0.16 | −54.4% |
| **vol-targeted** | +5.6% | 29.1% | **0.19** | **−40.5%** |

Vol targeting reduces drawdown ~26% and lifts Sharpe, **without adding return** — it is risk
management, not alpha. This is the only scientifically defensible use of a volatility model.

## 3. Fundamental balance is already priced in

Point-in-time WPIC supply/demand balance (47 quarterly vintages, Q3 2014 → Q2 2026) as a
predictor of forward 3-month returns:

| Test | Result |
|---|---|
| corr(deficit size, fwd return) | −0.011 (p=0.94) |
| R² | 0.0001 |
| deficit→up hit rate | 45% (coin flip) |

The deficit/surplus forecast has **no predictive power** — public fundamental data published
on a fixed schedule is absorbed at release. (Surplus quarters even rose *more* than deficit
quarters, opposite the thesis.) Testing with the final revised numbers instead of point-in-time
vintages would fabricate a fake signal — the 2024 balance was "final" −1096 koz but only −340 koz
when first published.

## Conclusion

Direction and fundamentals are unpredenceable; volatility is predictable. Ship the system as
a **risk engine** (GARCH position sizing + calibrated bands), not a price oracle.
