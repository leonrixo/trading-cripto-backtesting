import pandas as pd
from response import build_response


def test_build_response_sanitizes_nan_and_shapes_output():
    df = pd.DataFrame(
        {
            "close": [100.0, 102.0, 104.0],
            "fast_ma": [float("nan"), 101.0, 103.0],
            "slow_ma": [float("nan"), float("nan"), 102.0],
        },
        index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
    )
    result = {
        "equity_curve": pd.Series([1000.0, 1010.0, 1020.0], index=df.index),
        "trades": [
            {
                "entry_date": pd.Timestamp("2024-01-01"),
                "entry_price": 100.0,
                "exit_date": pd.Timestamp("2024-01-03"),
                "exit_price": 104.0,
                "pnl_pct": 0.04,
                "exit_reason": "signal",
            }
        ],
    }
    metrics = {
        "total_return": 0.02,
        "win_rate": 1.0,
        "max_drawdown": 0.0,
        "sharpe_ratio": 1.5,
        "num_trades": 1,
    }
    params = {
        "fast_window": 20,
        "slow_window": 50,
        "stop_loss_pct": 0.05,
        "initial_capital": 10_000.0,
    }

    response = build_response("BTC/USDT", df, result, metrics, params)

    assert response["symbol"] == "BTC/USDT"
    assert response["params"] == params
    assert response["dates"] == ["2024-01-01", "2024-01-02", "2024-01-03"]
    assert response["close"] == [100.0, 102.0, 104.0]
    assert response["fast_ma"][0] is None
    assert response["fast_ma"][1] == 101.0
    assert response["slow_ma"][1] is None
    assert response["equity_curve"] == [1000.0, 1010.0, 1020.0]
    assert response["trades"] == [
        {
            "entry_date": "2024-01-01",
            "entry_price": 100.0,
            "exit_date": "2024-01-03",
            "exit_price": 104.0,
            "pnl_pct": 0.04,
            "exit_reason": "signal",
        }
    ]
    assert response["metrics"]["num_trades"] == 1
    assert response["metrics"]["total_return"] == 0.02


def test_build_response_sanitizes_inf_and_nan_in_trades():
    """Ensure NaN and inf values in trades are converted to None for valid JSON."""
    df = pd.DataFrame(
        {
            "close": [100.0, 102.0, 104.0],
            "fast_ma": [101.0, 101.0, 103.0],
            "slow_ma": [102.0, 102.0, 102.0],
        },
        index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
    )
    result = {
        "equity_curve": pd.Series([1000.0, 1010.0, 1020.0], index=df.index),
        "trades": [
            {
                "entry_date": pd.Timestamp("2024-01-01"),
                "entry_price": float("nan"),
                "exit_date": pd.Timestamp("2024-01-02"),
                "exit_price": 102.0,
                "pnl_pct": 0.02,
                "exit_reason": "signal",
            },
            {
                "entry_date": pd.Timestamp("2024-01-02"),
                "entry_price": 102.0,
                "exit_date": pd.Timestamp("2024-01-03"),
                "exit_price": float("inf"),
                "pnl_pct": 0.03,
                "exit_reason": "signal",
            },
            {
                "entry_date": pd.Timestamp("2024-01-03"),
                "entry_price": 104.0,
                "exit_date": pd.Timestamp("2024-01-04"),
                "exit_price": 105.0,
                "pnl_pct": float("-inf"),
                "exit_reason": "stop_loss",
            },
        ],
    }
    metrics = {
        "total_return": float("inf"),
        "win_rate": 0.67,
        "max_drawdown": 0.0,
        "sharpe_ratio": 1.5,
        "num_trades": 3,
    }
    params = {
        "fast_window": 20,
        "slow_window": 50,
        "stop_loss_pct": 0.05,
        "initial_capital": 10_000.0,
    }

    response = build_response("BTC/USDT", df, result, metrics, params)

    assert response["params"] == params

    # Verify trades have None for NaN/inf values
    assert response["trades"][0]["entry_price"] is None
    assert response["trades"][1]["exit_price"] is None
    assert response["trades"][2]["pnl_pct"] is None

    # Verify metrics also sanitize inf values
    assert response["metrics"]["total_return"] is None
    assert response["metrics"]["sharpe_ratio"] == 1.5
    assert response["metrics"]["num_trades"] == 3
