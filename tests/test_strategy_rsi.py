import pandas as pd
import numpy as np
from strategy import compute_rsi, generate_scalping_signals


def test_compute_rsi_bounds():
    # Serie creciente: RSI debe ser alto (>70)
    prices = pd.Series([100 + i * 2 for i in range(30)], dtype=float)
    rsi = compute_rsi(prices, period=14)
    valid_rsi = rsi.dropna()
    assert (valid_rsi >= 0.0).all()
    assert (valid_rsi <= 100.0).all()
    assert valid_rsi.iloc[-1] > 70.0


def test_compute_rsi_falling():
    # Serie decreciente: RSI debe ser bajo (<30)
    prices = pd.Series([200 - i * 2 for i in range(30)], dtype=float)
    rsi = compute_rsi(prices, period=14)
    valid_rsi = rsi.dropna()
    assert valid_rsi.iloc[-1] < 30.0


def test_generate_scalping_signals_columns_and_shift():
    dates = pd.date_range("2026-01-01", periods=50, freq="1h")
    # Precio oscilante que sube
    np.random.seed(42)
    close = 100.0 + np.cumsum(np.random.randn(50) + 0.5)
    df = pd.DataFrame({"close": close}, index=dates)

    out = generate_scalping_signals(df, fast_window=5, slow_window=10, rsi_period=7)

    assert "fast_ma" in out.columns
    assert "slow_ma" in out.columns
    assert "rsi" in out.columns
    assert "signal" in out.columns

    # La primera señal siempre debe ser 0 por el shift(1)
    assert out["signal"].iloc[0] == 0
    # Los valores de señal son binarios 0 o 1
    assert set(out["signal"].unique()).issubset({0, 1})

