import pytest
import pandas as pd
import numpy as np
from grid_engine import run_grid_backtest


def test_grid_invalid_params():
    df = pd.DataFrame({"close": [100.0, 102.0, 101.0]})
    with pytest.raises(ValueError, match="lower_price debe ser menor"):
        run_grid_backtest(df, lower_price=120, upper_price=100)

    with pytest.raises(ValueError, match="num_grids debe ser al menos 2"):
        run_grid_backtest(df, lower_price=100, upper_price=120, num_grids=1)


def test_grid_oscillating_market_generates_realized_profit():
    # Mercado oscilante: 100 -> 95 -> 105 -> 95 -> 105
    dates = pd.date_range("2026-01-01", periods=10, freq="1h")
    prices = [100, 96, 92, 98, 104, 93, 103, 94, 104, 100]
    df = pd.DataFrame({
        "close": prices,
        "high": [p + 1.0 for p in prices],
        "low": [p - 1.0 for p in prices],
    }, index=dates)

    result = run_grid_backtest(
        df=df,
        lower_price=90.0,
        upper_price=110.0,
        num_grids=4,
        initial_capital=10_000.0,
        fee_pct=0.001,
    )

    assert result["num_grid_buys"] > 0
    assert result["num_grid_sells"] > 0
    assert result["realized_profit"] > 0
    assert len(result["grid_levels"]) == 5
    assert len(result["equity_curve"]) == len(df)


def test_grid_stop_loss_trigger():
    # Precio se desploma
    dates = pd.date_range("2026-01-01", periods=5, freq="1h")
    prices = [100.0, 95.0, 85.0, 70.0, 60.0]
    df = pd.DataFrame({
        "close": prices,
        "high": prices,
        "low": prices,
    }, index=dates)

    result = run_grid_backtest(
        df=df,
        lower_price=80.0,
        upper_price=120.0,
        num_grids=4,
        initial_capital=10_000.0,
        stop_loss_pct=0.05,  # 80 * 0.95 = 76 stop price
    )

    assert result["stopped_out"] is True
    exit_trades = [t for t in result["trades"] if t["type"] == "stop_loss_exit"]
    assert len(exit_trades) >= 1

