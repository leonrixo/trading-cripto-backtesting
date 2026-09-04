import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

import server
from server import app

client = TestClient(app)


def _make_synthetic_1h_ohlcv(n=120):
    dates = pd.date_range("2026-01-01", periods=n, freq="1h")
    # Oscilación suave para generar cruces y niveles de malla
    close = 100.0 + 10.0 * np.sin(np.linspace(0, 4 * np.pi, n))
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.full(n, 500.0),
        },
        index=dates,
    )
    df.index.name = "timestamp"
    return df


def test_scalping_1h_endpoint(monkeypatch):
    synthetic = _make_synthetic_1h_ohlcv(100)
    monkeypatch.setattr(server, "fetch_ohlcv", lambda symbol, timeframe="1h": synthetic)

    response = client.post(
        "/api/backtest",
        json={"symbol": "BTC/USDT", "strategy_type": "scalping_1h"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["params"]["strategy"] == "scalping_1h"
    assert "rsi" in data
    assert len(data["rsi"]) == len(data["close"])
    assert "trades" in data
    assert "metrics" in data


def test_grid_endpoint_happy_path(monkeypatch):
    synthetic = _make_synthetic_1h_ohlcv(100)
    monkeypatch.setattr(server, "fetch_ohlcv", lambda symbol, timeframe="1h": synthetic)

    response = client.post(
        "/api/backtest/grid",
        json={
            "symbol": "BTC/USDT",
            "lower_price": 85.0,
            "upper_price": 115.0,
            "num_grids": 6,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "grid"
    assert len(data["grid_levels"]) == 7
    assert data["metrics"]["num_trades"] >= 0
    assert "realized_profit" in data["metrics"]
    assert "equity_curve" in data

