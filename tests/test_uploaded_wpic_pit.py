from platinum.wpic_pit_prepare import prepare

def test_uploaded_wpic_pit_integrity(tmp_path):
    r=prepare("data/verified/platinum_supply_demand_pit_user_extracted.csv",tmp_path)
    assert r["exact_current_year_vintages"]==31
    assert r["accepted_vintages"]==29
    assert r["excluded_vintages"]==["Q1_2024","Q2_2024"]
    assert len(r["metrics"])==10
    assert not r["value_corrections_made"]
