"""Canonical metal registry. Futures charts are research references, not licensed spot benchmarks."""
METALS = {
    "platinum": {"label": "Platinum", "symbol": "PL=F", "ticker": "PL", "currency": "USD", "unit": "USD/troy_oz"},
    "gold": {"label": "Gold", "symbol": "GC=F", "ticker": "GC", "currency": "USD", "unit": "USD/troy_oz"},
    "silver": {"label": "Silver", "symbol": "SI=F", "ticker": "SI", "currency": "USD", "unit": "USD/troy_oz"},
    "palladium": {"label": "Palladium", "symbol": "PA=F", "ticker": "PA", "currency": "USD", "unit": "USD/troy_oz"},
}
NEW_METALS = ("gold", "silver", "palladium")
LOCK_START = "2026-11-04"
ORIGIN_END = "2027-07-30"
SCORE_NOT_BEFORE_UTC = "2027-12-16T00:00:00Z"
