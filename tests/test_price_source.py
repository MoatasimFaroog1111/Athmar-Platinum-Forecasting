import pytest
from platinum.price_source import parse_chart


def payload(closes, timestamps=None, currency="USD"):
    if timestamps is None:
        timestamps = [1577836800 + i * 86400 for i in range(len(closes))]
    return {"chart": {"error": None, "result": [
        {"meta": {"currency": currency}, "timestamp": timestamps,
         "indicators": {"quote": [{"close": closes}]}}
    ]}}


def test_chart_requires_sufficient_real_bars():
    with pytest.raises(ValueError, match="Not enough"):
        parse_chart(payload([1000.0, 1001.0]))


def test_valid_chart_parses_unit_test_fixture():
    sample = payload([1000 + i for i in range(300)])
    df = parse_chart(sample)
    assert len(df) == 300
    assert df.Close.iloc[0] == 1000


def test_rejects_wrong_currency():
    with pytest.raises(ValueError, match="Expected USD"):
        parse_chart(payload([1000.0], currency="EUR"))


def test_rejects_duplicates():
    with pytest.raises(ValueError, match="Duplicate"):
        parse_chart(payload([1000.0] * 300, timestamps=[1577836800] * 300))
