# WPIC point-in-time pre-approval rerun — 2026-11-02

GitHub Actions run: 41458249266

## Uploaded WPIC dataset audit
- Input rows: 1,880
- Input vintages: 47
- Exact-date current-year vintages: 31
- Accepted after integrity checks: 29
- Excluded without correction: Q1_2024 and Q2_2024
- Availability rule: use exact publication date only, then delay availability until the next UTC day because release time is not present.
- Ten annual current-year WPIC measures used: above-ground stocks, automotive, balance, industrial, investment, jewellery, recycling, total demand, total mining supply, total supply.

## Ablation
### Market-only
Gate: FAIL / BLOCK_APPROVAL
Point champion at 1/5/20/60/90 days: no-change.
Coverage at nominal 90%: 83.06%, 81.78%, 84.84%, 95.34%, 83.91%.

### Market + verified-date WPIC PIT
Gate: FAIL / BLOCK_APPROVAL
Point champion at 1/5/20/60/90 days: no-change.
Coverage at nominal 90%: 83.06%, 81.78%, 84.84%, 95.34%, 83.91%.

WPIC changed candidate-model validation errors but did not beat the no-change baseline.
Examples:
- 20d boost validation MAE improved from 0.05172 market-only to 0.05080 with WPIC, still worse than no-change 0.03768.
- 60d boost improved from 0.06445 to 0.06283, still worse than no-change 0.04534.
- 90d boost improved from 0.07373 to 0.06128, still worse than no-change 0.03332.

### Market + WPIC + CFTC assumed timing
Gate: FAIL / BLOCK_APPROVAL.
Source availability verification is false because historical CFTC timing uses the conservative assumed embargo.
Point champion remains no-change across all tested horizons.

## Decision
WPIC PIT integration is operational and auditable, but it does not justify approval under the current model/features/calibration. No production forecast or 2027 probability claim should be released from this run.
