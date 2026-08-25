import pandas as pd
from data import fetch_ohlcv


def fake_fetch_fn(exchange, symbol, timeframe, since_ms, limit):
    # Simula 3 velas diarias con timestamps en milisegundos.
    base_ms = 1_700_000_000_000
    day_ms = 24 * 60 * 60 * 1000
    return [
        [base_ms + 0 * day_ms, 100, 105, 95, 102, 10.0],
        [base_ms + 1 * day_ms, 102, 108, 100, 106, 12.0],
        [base_ms + 2 * day_ms, 106, 110, 104, 108, 8.0],
    ]


def test_fetch_ohlcv_downloads_and_caches(tmp_path):
    df = fetch_ohlcv("BTC/USDT", fetch_fn=fake_fetch_fn, cache_dir=tmp_path)

    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 3
    assert (tmp_path / "BTC_USDT_1d.csv").exists()


def test_fetch_ohlcv_uses_cache_without_calling_fetch_fn(tmp_path):
    def fetch_fn_that_should_not_run(*args, **kwargs):
        raise AssertionError("fetch_fn no debió llamarse: se esperaba usar el cache")

    fetch_ohlcv("BTC/USDT", fetch_fn=fake_fetch_fn, cache_dir=tmp_path)
    df = fetch_ohlcv("BTC/USDT", fetch_fn=fetch_fn_that_should_not_run, cache_dir=tmp_path)

    assert len(df) == 3
