from pathlib import Path

from data import fetch_ohlcv
from strategy import generate_signals
from backtest import run_backtest
from metrics import compute_metrics
from report import generate_report

SYMBOLS = ["BTC/USDT", "ETH/USDT"]
FAST_WINDOW = 20
SLOW_WINDOW = 50
STOP_LOSS_PCT = 0.05
INITIAL_CAPITAL = 10_000.0


def run_for_symbol(symbol: str, output_dir: Path) -> dict:
    df = fetch_ohlcv(symbol)
    df = generate_signals(df, FAST_WINDOW, SLOW_WINDOW)
    result = run_backtest(df, initial_capital=INITIAL_CAPITAL, stop_loss_pct=STOP_LOSS_PCT)
    metrics = compute_metrics(result["equity_curve"], result["trades"])
    generate_report(df, result["equity_curve"], metrics, symbol, output_dir, result["trades"])
    return metrics


def main():
    output_dir = Path(__file__).resolve().parent.parent / "reports"
    for symbol in SYMBOLS:
        try:
            metrics = run_for_symbol(symbol, output_dir)
            print(
                f"{symbol}: total_return={metrics['total_return']:.2%} "
                f"win_rate={metrics['win_rate']:.2%} "
                f"max_drawdown={metrics['max_drawdown']:.2%} "
                f"sharpe_ratio={metrics['sharpe_ratio']:.2f} "
                f"num_trades={metrics['num_trades']}"
            )
        except Exception as e:
            print(f"{symbol}: FAILED - {e}")
            continue


if __name__ == "__main__":
    main()
