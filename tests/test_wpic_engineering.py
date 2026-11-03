import json
from pathlib import Path
from platinum.wpic_engineering import engineer

def test_engineered_wpic_features_from_uploaded_vintages(tmp_path):
    result=engineer("data/verified/platinum_supply_demand_pit_user_extracted.csv",tmp_path)
    assert result["excluded_vintages"]==["Q1_2024","Q2_2024"]
    assert not result["value_corrections_made"]
    assert set(result["feature_counts"])=={
        "wpic_balance_to_demand_ratio",
        "wpic_total_supply_yoy_growth",
        "wpic_total_demand_yoy_growth",
        "wpic_total_supply_revision_pct",
        "wpic_total_demand_revision_pct",
        "wpic_balance_revision_to_demand",
    }
    assert all(v>=12 for v in result["feature_counts"].values())
