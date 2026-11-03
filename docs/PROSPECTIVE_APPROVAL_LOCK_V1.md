# ATHMAR Platinum — Prospective Approval Lock V1

Locked on: 2026-11-03
Protocol: ATHMAR_PLATINUM_APPROVAL_V1
Latest verification run: 41595442161

## Nested Walk-Forward selection
All selection/calibration data are strictly before 2026-11-03. Any sample whose target reaches the lock start is excluded.

Locked candidates:
- 1 business day: price_only / no_change; q90=0.04319172393303283
- 5 business days: price_only / no_change; q90=0.08872636237365583
- 20 business days: price_only / no_change; q90=0.21199950404260193
- 60 business days: price_only / no_change; q90=0.34644730362401965
- 90 business days: market_wpic_all / ridge_1.0; q90=0.45296965936250544

Pre-lock sample signatures:
- 1d 3663bc7a1f1b410da01b
- 5d 5c77455179279df0b21e
- 20d 346abf6fda738502e38d
- 60d 20686ba98e41369af2ba
- 90d 0380ab116ffa61e7d225

The 90d feature group includes verified next-day cross-market inputs, WPIC absolute PIT levels, and engineered WPIC vintage revision/ratio/growth features. CFTC assumed historical publication timing is excluded from the approval lock.

## Prospective holdout
- Origin start: 2026-11-03
- Origin end: 2027-07-30
- Scoring prohibited before: 2027-12-15T00:00:00Z
- Minimum matured origins per horizon: 100
- Nominal interval coverage: 90%

Approval requires every horizon to satisfy:
1. at least 1% MAE improvement versus no-change;
2. 90% nominal coverage lies inside the 95% Wilson interval;
3. realized coverage between 87% and 93%;
4. source availability is verified.

## Governance
No feature/model/interval/threshold tuning is allowed for V1 after lock. Any change requires a new protocol and a new future holdout.

CI verification:
- FROZEN_MODEL_LOCK_MATCH_CONFIRMED
- prospective status = LOCKED
- metrics_revealed = false
- model_lock_sha256 = 9a98f8d44d07d5e33260377abf526e9bcf7517d7e183359cfd8688da25ebfdfb

A real approval decision is intentionally impossible before the prospective holdout is eligible for scoring.
