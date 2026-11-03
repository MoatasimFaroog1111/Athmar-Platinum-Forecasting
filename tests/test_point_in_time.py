import pandas as pd
import pytest
from platinum.point_in_time import asof_feature
from platinum.cftc_calendar import require_verified_calendar

def test_release_no_leak():
    dates=pd.DataFrame({"Date":["2026-01-02","2026-01-05"]})
    release=pd.DataFrame({"period_end":["2025-12-31"],"available_at":["2026-01-03T16:00:00Z"],"value":[120.0],"source":["WPIC"],"unit":["koz"]})
    result=asof_feature(dates,release,"supply")
    assert pd.isna(result.supply.iloc[0])
    assert result.supply.iloc[1]==120

def test_calendar_required():
    with pytest.raises(ValueError,match="calendar"):
        require_verified_calendar(pd.DataFrame({"report_date":["2026-01-06"]}),pd.DataFrame())
