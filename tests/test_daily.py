from pathlib import Path
import pandas as pd
import pytest
from platinum.daily import OZ_PER_KG, load_daily, fit_and_forecast

def test_missing_file_rejected(tmp_path):
    with pytest.raises(ValueError, match="missing"):
        load_daily(tmp_path / "missing.csv")

def test_unit_conversion():
    assert abs(OZ_PER_KG * 1000 - 32150.7465686) < 0.000001

def test_synthetic_data_for_unit_testing_only(tmp_path):
    # Synthetic inputs test wiring only, NEVER imply market validation.
    import numpy as np
    dates = pd.bdate_range("2024-01-01", periods=320)
    frame = pd.DataFrame({"Date": dates, "Close": 1000 + np.linspace(0, 150, len(dates))})
    path = tmp_path / "test_only.csv"
    frame.to_csv(path, index=False)
    result = fit_and_forecast(path, "TEST_ONLY_SYNTHETIC", tmp_path / "out")
    assert result["test_observations"] > 0
    assert (tmp_path / "out" / "backtest.json").is_file()
    assert (tmp_path / "out" / "forecasts_experimental.csv").is_file()
