import pandas as pd
from metrics import compute_metrics


def test_total_return_and_win_rate():
    equity_curve = pd.Series([1000, 1100, 1050, 1200])
    trades = [
        {"pnl_pct": 0.10},
        {"pnl_pct": -0.05},
        {"pnl_pct": 0.15},
    ]

    result = compute_metrics(equity_curve, trades)

    assert abs(result["total_return"] - 0.2) < 1e-6
    assert abs(result["win_rate"] - (2 / 3)) < 1e-6
    assert result["num_trades"] == 3


def test_max_drawdown_is_negative_when_equity_dips():
    equity_curve = pd.Series([1000, 1200, 900, 1300])

    result = compute_metrics(equity_curve, trades=[])

    # De pico 1200 a valle 900 es una caída del 25%.
    assert abs(result["max_drawdown"] - (-0.25)) < 1e-6
    assert result["win_rate"] == 0.0
