from datetime import datetime, timezone

import pandas as pd
from data import fetch_ohlcv


def fake_fetch_fn(exchange, symbol, timeframe, since_ms, limit):
    # Simula 3 velas diarias con timestamps en milisegundos.
    # 2023-11-14T22:13:20Z, muy en el pasado respecto a cualquier "hoy" real,
    # para que la lógica de "descartar la vela de hoy" nunca recorte estos datos.
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


def test_fetch_ohlcv_drops_todays_still_forming_candle(tmp_path):
    day_ms = 24 * 60 * 60 * 1000
    today_midnight_utc = datetime.combine(
        datetime.now(timezone.utc).date(), datetime.min.time(), tzinfo=timezone.utc
    )
    today_ms = int(today_midnight_utc.timestamp() * 1000)

    def fetch_fn_with_todays_candle(exchange, symbol, timeframe, since_ms, limit):
        return [
            [today_ms - 2 * day_ms, 100, 105, 95, 102, 10.0],
            [today_ms - 1 * day_ms, 102, 108, 100, 106, 12.0],
            [today_ms, 106, 110, 104, 108, 8.0],  # vela de "hoy", aún en formación
        ]

    df = fetch_ohlcv("ETH/USDT", fetch_fn=fetch_fn_with_todays_candle, cache_dir=tmp_path)

    # La vela de hoy debe descartarse: solo quedan las 2 anteriores, y esa
    # última fila (close=108) no debe aparecer ni en el DataFrame ni en el cache.
    assert len(df) == 2
    assert 108 not in df["close"].values

    cached = pd.read_csv(tmp_path / "ETH_USDT_1d.csv")
    assert len(cached) == 2


def test_fetch_ohlcv_refresh_true_bypasses_cache(tmp_path):
    fetch_ohlcv("BTC/USDT", fetch_fn=fake_fetch_fn, cache_dir=tmp_path)

    calls = {"count": 0}

    def counting_fetch_fn(*args, **kwargs):
        calls["count"] += 1
        return fake_fetch_fn(*args, **kwargs)

    fetch_ohlcv("BTC/USDT", fetch_fn=counting_fetch_fn, cache_dir=tmp_path, refresh=True)

    assert calls["count"] == 1
