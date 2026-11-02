import numpy as np
from platinum.validation import evaluate
def test_holdout_separate_from_selection():
    prices=np.exp(6.9+np.cumsum(np.sin(np.arange(1200)/11)/100))
    result=evaluate(prices,horizons=(1,5))
    assert result["1"]["selected_on"]=="pre_holdout_3_walkforward_folds"
    assert result["5"]["holdout_size"]>35
