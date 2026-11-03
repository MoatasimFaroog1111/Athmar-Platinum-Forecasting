import pandas as pd
import numpy as np
import pytest
from platinum.feature_store import initialize,join_as_published
from platinum.model_competition import make_dataset,competition

def test_no_future_release_leakage():
    prices=pd.DataFrame({"Date":["2026-01-01","2026-01-02","2026-01-03"],"Close":[100,101,102]})
    releases=pd.DataFrame({"published_at":["2026-01-03T12:00:00Z"],"wpic_value":[42]})
    result=join_as_published(prices,releases,"wpic_value")
    assert pd.isna(result.iloc[0]["wpic_value"])
    assert pd.isna(result.iloc[1]["wpic_value"])
    assert result.iloc[2]["wpic_value"]==42

def test_store_schema(tmp_path):
    import sqlite3
    db=tmp_path/"test.sqlite"
    initialize(db)
    with sqlite3.connect(db) as conn:
        names={x[0] for x in conn.execute("select name from sqlite_master where type='table'")}
    assert {"price_bars","fundamental_releases","cot_releases","model_runs"} <= names

def test_exact_horizon_label():
    prices=np.exp(np.arange(150)/100)
    x,y,origins=make_dataset(prices,5)
    assert len(x)==len(y)==len(origins)
    assert abs(y[0]-0.05)<1e-8

def test_competition_with_synthetic_unit_fixture():
    prices=np.exp(np.cumsum(np.r_[6.9, np.sin(np.arange(349)/10)/200]))
    result,champions=competition(prices,horizons=(1,5))
    assert set(champions)=={1,5}
    assert all(x["test_size"] >=25 for x in result.values())

def test_future_publication_cannot_be_backfilled():
    prices=pd.DataFrame({"Date":["2026-01-01","2026-01-02"],"Close":[100,101]})
    releases=pd.DataFrame({"published_at":["2026-01-05T12:00:00Z"],"cot_value":[42]})
    assert join_as_published(prices,releases,"cot_value")["cot_value"].isna().all()
