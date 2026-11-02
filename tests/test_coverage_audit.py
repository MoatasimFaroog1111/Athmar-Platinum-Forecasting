import numpy as np
from platinum.coverage_audit import assess

def test_disjoint_conformal_evaluation():
    # Synthetic fixture tests only isolation and I/O, not financial coverage.
    rets=np.sin(np.arange(1300)/9)/100
    prices=1000*np.exp(np.cumsum(rets))
    result=assess(prices)
    assert result["selection_calibration_test_disjoint"]
    assert 0 <= result["holdout_coverage"] <= 1
    assert result["calibration_size"]>=80
    assert result["test_size"]>=80
    assert not result["fundamentals_used"]
