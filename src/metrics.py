import numpy as np
import pandas as pd


def compute_metrics(equity_curve: pd.Series, trades: list, periods_per_year: int = 365) -> dict:
    """
    equity_curve: valor del portafolio a través del tiempo (output de run_backtest).
    trades: lista de dicts con clave 'pnl_pct' (output de run_backtest).
    """
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1

    if trades:
        wins = sum(1 for t in trades if t["pnl_pct"] > 0)
        win_rate = wins / len(trades)
    else:
        win_rate = 0.0

    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    max_drawdown = drawdown.min()

    period_returns = equity_curve.pct_change().dropna()
    if period_returns.std() > 0:
        sharpe_ratio = (period_returns.mean() / period_returns.std()) * np.sqrt(periods_per_year)
    else:
        sharpe_ratio = 0.0

    return {
        "total_return": total_return,
        "win_rate": win_rate,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "num_trades": len(trades),
    }
