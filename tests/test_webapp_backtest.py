import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

import server
from server import app

client = TestClient(app)


def test_backtest_rejects_unsupported_symbol():
    response = client.post("/api/backtest", json={"symbol": "FAKE/USDT"})
    assert response.status_code == 400


def _make_synthetic_ohlcv(n=90):
    """OHLCV sintético con suficientes filas para superar SLOW_WINDOW y con una
    tendencia (subida + caída) que produce al menos un cruce de medias, sin
    tocar la red."""
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    trend = np.concatenate([
        np.linspace(100.0, 160.0, n // 2),
        np.linspace(160.0, 110.0, n - n // 2),
    ])
    noise = np.sin(np.arange(n) * 0.7) * 0.8
    close = trend + noise
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.full(n, 1000.0),
        },
        index=dates,
    )
    df.index.name = "timestamp"
    return df


def test_backtest_happy_path_returns_full_response(monkeypatch):
    synthetic = _make_synthetic_ohlcv()
    monkeypatch.setattr(server, "fetch_ohlcv", lambda symbol: synthetic)

    response = client.post("/api/backtest", json={"symbol": "BTC/USDT"})

    assert response.status_code == 200

    body = response.json()
    expected_keys = {
        "symbol", "dates", "close", "fast_ma", "slow_ma",
        "equity_curve", "trades", "metrics", "params",
    }
    assert set(body.keys()) == expected_keys

    assert len(body["dates"]) == len(body["close"]) == len(body["equity_curve"])

    assert "NaN" not in response.text
    assert "Infinity" not in response.text
