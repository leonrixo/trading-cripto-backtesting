import pandas as pd
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

    png_path = generate_report(df, equity_curve, metrics, "BTC/USDT", tmp_path)

    assert png_path.exists()
    metrics_path = tmp_path / "BTC_USDT_metrics.txt"
    assert metrics_path.exists()
    content = metrics_path.read_text()
    assert "total_return" in content
