import pandas as pd
from backtest import run_backtest


def test_opens_and_closes_position_on_signal_change():
    df = pd.DataFrame({
        "close":  [100, 100, 110, 120, 120],
        "signal": [0,   1,   1,   1,   0],
    })

    result = run_backtest(df, initial_capital=1000.0, stop_loss_pct=0.5, position_size_pct=1.0)

    assert len(result["trades"]) == 1
    trade = result["trades"][0]
    assert trade["exit_reason"] == "signal"
    assert trade["entry_price"] == 100
    assert trade["exit_price"] == 120
    assert abs(trade["pnl_pct"] - 0.2) < 1e-9
    # El equity final debe reflejar la ganancia de 100 -> 120 (20%).
    assert abs(result["equity_curve"].iloc[-1] - 1200.0) < 1e-6


def test_stop_loss_closes_position_early():
    df = pd.DataFrame({
        "close":  [100, 100, 90, 80, 80],
        "signal": [0,   1,   1,  1,  1],
    })

    result = run_backtest(df, initial_capital=1000.0, stop_loss_pct=0.05, position_size_pct=1.0)

    assert len(result["trades"]) == 1
    assert result["trades"][0]["exit_reason"] == "stop_loss"
    # Con stop_loss_pct=0.05 sobre entrada de 100, debe salir en <= 95, o sea en la barra de 90.
    assert result["trades"][0]["exit_price"] == 90
