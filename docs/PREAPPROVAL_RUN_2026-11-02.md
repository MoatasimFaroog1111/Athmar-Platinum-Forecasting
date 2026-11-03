# Pre-approval gate — 2026-11-02

GitHub Actions run: 41452836757

Research inputs:
- Platinum daily futures (PL=F) research chart.
- Gold, palladium, silver, dollar index, ZAR/USD, US 10Y market proxies.
- CFTC managed-money net positions, real archive values but **assumed 10-day embargo** for historical availability.
- WPIC vintage archive dates are documented, but a complete vintage-by-vintage numeric series is not yet mapped into the model.

Gate result: **BLOCK_APPROVAL**.

Per-horizon 90% interval coverage on untouched test data:
- 1 day: 83.06% (248 observations)
- 5 days: 81.78% (247 observations)
- 20 days: 84.84% (244 observations)
- 60 days: 95.34% (236 observations)
- 90 days: 83.91% (230 observations)

The selected point forecast for all tested horizons was the no-change baseline. Cross-market/CFTC candidates did not beat it on validation.

Hard blockers:
1. CFTC historical exact release timestamps are not available as a complete official archive; current feature uses a conservative research embargo and is not source-verified.
2. WPIC vintage numerical metrics are not yet fully extracted across historical publications; current reports can revise history.
3. 90% interval coverage fails on 1/5/20/90-day horizons.
4. No production forecast, trading signal, or approval is authorized by this run.
