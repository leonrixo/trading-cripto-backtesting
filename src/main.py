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
    generate_report(df, result["equity_curve"], metrics, symbol, output_dir)
    return metrics


def main():
    output_dir = Path(__file__).resolve().parent.parent / "reports"
    for symbol in SYMBOLS:
        metrics = run_for_symbol(symbol, output_dir)
        print(f"{symbol}: {metrics}")


if __name__ == "__main__":
    main()
