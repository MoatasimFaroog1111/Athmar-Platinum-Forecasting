import pandas as pd
from platinum.cftc_schedule_2026 import scheduled_releases_2026,associate_report_publication
from platinum.point_in_time import asof_feature

def test_cftc_holiday_delays_and_dst():
    calendar=scheduled_releases_2026()
    assert len(calendar)>45
    # 2026-06-16 Tuesday => 2026-06-22 Monday delayed by holiday
    assert associate_report_publication(["2026-06-16"])[0].startswith("2026-06-22T")
    # January EST 15:30 => 20:30 UTC
    assert any(x.startswith("2026-01-09T20:30:00") for x in calendar.published_at)

def test_source_published_q2_not_available_on_june_30():
    releases=pd.read_csv("data/verified/wpic_q2_2026_news_release.csv")
    one=releases[releases.metric=="platinum_q2_total_supply"].copy()
    result=asof_feature(pd.DataFrame({"Date":["2026-07-01","2026-09-11"]}),one,"wpic_supply")
    assert pd.isna(result.wpic_supply.iloc[0])
    assert result.wpic_supply.iloc[1]==1906
