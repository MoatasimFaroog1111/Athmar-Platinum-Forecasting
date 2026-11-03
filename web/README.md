# Athmar Platinum Intelligence

Premium read-only dashboard over the existing forecasting engine.

## Safety contract
The UI never scores or reveals prospective holdout metrics. It renders the locked V1 protocol, model stack, WPIC fundamentals, live/shadow market state and append-only forecast journal when those feeds exist.

## Run locally
```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000.

By default `/api/state` returns the checked-in fail-closed bootstrap. Set `ATHMAR_STATE_URL` to a trusted read-only JSON endpoint produced by the shadow engine to display live data.

## Deployment
Recommended layout:
- Vercel: `web/`
- Shadow engine/API: existing Python runtime or VPS
- `ATHMAR_STATE_URL`: HTTPS read-only state endpoint

No model mutation, trading action, holdout scoring or approval action belongs in this frontend.
