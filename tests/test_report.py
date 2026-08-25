import pandas as pd
import report as report_module
from report import generate_report


def test_generate_report_creates_png_and_metrics_file(tmp_path):
    df = pd.DataFrame({
        "close":   [100, 102, 104, 103, 105],
        "fast_ma": [None, None, 102.0, 103.0, 104.0],
        "slow_ma": [None, None, None, None, 102.8],
        "signal":  [0, 0, 1, 1, 0],
    })
    equity_curve = pd.Series([1000, 1000, 1020, 1010, 1030])
    metrics = {"total_return": 0.03, "win_rate": 1.0, "max_drawdown": -0.01,
               "sharpe_ratio": 1.2, "num_trades": 1}
    trades = [
        {
            "entry_date": 2,
            "exit_date": 4,
            "entry_price": 104,
            "exit_price": 105,
            "pnl_pct": (105 - 104) / 104,
            "exit_reason": "signal",
        },
    ]

    png_path = generate_report(df, equity_curve, metrics, "BTC/USDT", tmp_path, trades)

    assert png_path.exists()
    metrics_path = tmp_path / "BTC_USDT_metrics.txt"
    assert metrics_path.exists()
    content = metrics_path.read_text()
    assert "total_return" in content


def test_generate_report_markers_come_from_trades_not_signal_column(tmp_path, monkeypatch):
    # La columna signal solo tiene UNA transición 0->1 y una 1->0 (lo que antes
    # habría producido 1 entry marker y 1 exit marker). Pero pasamos 2 trades
    # explícitos (uno de ellos un stop_loss que la columna signal jamás refleja).
    # Los marcadores dibujados deben salir de `trades`, no de la columna signal.
    df = pd.DataFrame({
        "close":   [100, 102, 104, 103, 105, 107, 106],
        "fast_ma": [None, None, 102.0, 103.0, 104.0, 105.0, 105.5],
        "slow_ma": [None, None, None, None, 102.8, 103.5, 104.0],
        "signal":  [0, 0, 1, 1, 1, 1, 1],
    })
    equity_curve = pd.Series([1000, 1000, 1020, 1010, 1030, 1050, 1040])
    metrics = {"total_return": 0.04, "win_rate": 0.5, "max_drawdown": -0.01,
               "sharpe_ratio": 1.0, "num_trades": 2}
    trades = [
        {
            "entry_date": 2,
            "exit_date": 3,
            "entry_price": 104,
            "exit_price": 103,
            "pnl_pct": (103 - 104) / 104,
            "exit_reason": "stop_loss",
        },
        {
            "entry_date": 4,
            "exit_date": 6,
            "entry_price": 105,
            "exit_price": 106,
            "pnl_pct": (106 - 105) / 105,
            "exit_reason": "end_of_data",
        },
    ]

    # generate_report closes its figure internally (plt.close(fig)) before
    # returning, so we can't inspect it via plt.gcf() afterwards. Instead we
    # spy on plt.subplots to capture the actual axes objects it created;
    # those Python objects stay alive (and inspectable) as long as we hold a
    # reference, even after matplotlib "closes" the figure.
    captured = {}
    original_subplots = report_module.plt.subplots

    def spy_subplots(*args, **kwargs):
        fig, axes = original_subplots(*args, **kwargs)
        captured["axes"] = axes
        return fig, axes

    monkeypatch.setattr(report_module.plt, "subplots", spy_subplots)

    generate_report(df, equity_curve, metrics, "BTC/USDT", tmp_path, trades)

    ax_price, _ax_equity = captured["axes"]
    total_marker_points = sum(len(c.get_offsets()) for c in ax_price.collections)

    # 2 entries + 2 exits = 4 marker points total, drawn across the entry/
    # normal-exit/stop-loss-exit scatter series. The signal column alone only
    # has one 0->1 and one 1->0 transition, so the old signal-based logic
    # would have produced just 2 marker points here — this proves the
    # markers now come from `trades`.
    assert total_marker_points == len(trades) * 2
