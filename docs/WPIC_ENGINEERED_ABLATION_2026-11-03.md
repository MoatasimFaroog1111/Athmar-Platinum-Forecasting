# WPIC engineered-feature ablation — 2026-11-03

GitHub Actions run: 41594055340

## Engineered WPIC PIT features
- balance / total demand: 29 releases
- total supply YoY growth: 29
- total demand YoY growth: 29
- total supply vintage revision %: 20
- total demand vintage revision %: 20
- balance revision / total demand: 20

All use exact publication-date vintages only, next-UTC-day availability, no value correction, and the same Q1_2024/Q2_2024 integrity exclusions.

## Holdout identity
The CI assertion printed `IDENTICAL_HOLDOUT_SPLITS_CONFIRMED`.
Split signatures were unchanged between WPIC absolute levels and engineered WPIC:
- 1d: 695e8d9663a46f12
- 5d: 31ddd3d179359710
- 20d: 7f6dcb907a00e438
- 60d: e39a0b98e45373e0
- 90d: 4cb979e3bdfc757d

## Gate result
Overall: **FAIL / BLOCK_APPROVAL**.

### 1-day
Engineered Ridge validation MAE = 0.0136173 vs no-change 0.0136675, so Ridge was selected.
Untouched test MAE = 0.0357472 vs baseline 0.0240410 (~48.7% worse).
Coverage = 70.97% vs nominal 90%.
Point and coverage gates both fail.

### 5/20/60/90 days
No-change remained the selected champion.
Coverage remained 81.78%, 84.84%, 95.34%, and 83.91%, respectively.
Therefore none of the five horizons passes the full gate.

## Comparison with absolute WPIC levels
The engineered representation materially improved Ridge validation MAE at 1d and 5d and at 90d, but did not create robust out-of-sample skill. At 1d the apparent validation gain reversed sharply in the held-out test, demonstrating overfitting.

## Research integrity consequence
This fixed benchmark holdout has now been observed in repeated development comparisons. It remains useful for documenting this experiment, but it must not be treated as an untouched final approval sample for subsequent tuning. Future approval requires a new locked/prospective holdout or nested evaluation designed before observing its outcomes.

No production approval, 2027 probabilistic release, merge, or trading action is authorized by this run.
