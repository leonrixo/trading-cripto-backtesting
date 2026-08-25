from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def generate_report(
    df: pd.DataFrame,
    equity_curve: pd.Series,
    metrics: dict,
    symbol: str,
    output_dir,
    trades: list,
) -> Path:
    """
    df: output de strategy.generate_signals (columnas close, fast_ma, slow_ma, signal).
    trades: lista de dicts (output de backtest.run_backtest) con entry_date/entry_price/
    exit_date/exit_price/exit_reason. Los marcadores de entrada/salida en la gráfica
    se derivan de estos trades reales (no de las transiciones de la columna signal),
    para que stop-loss y end_of_data también queden visibles.
    Guarda un PNG con precio+señales+equity curve, y un .txt con las métricas.
    Regresa la ruta al PNG.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_symbol = symbol.replace("/", "_")

    fig, (ax_price, ax_equity) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    ax_price.plot(df.index, df["close"], label="close", color="black", linewidth=1)
    ax_price.plot(df.index, df["fast_ma"], label="fast_ma", linewidth=1)
    ax_price.plot(df.index, df["slow_ma"], label="slow_ma", linewidth=1)

    entry_dates = [t["entry_date"] for t in trades]
    entry_prices = [t["entry_price"] for t in trades]
    normal_exit_dates = [t["exit_date"] for t in trades if t["exit_reason"] != "stop_loss"]
    normal_exit_prices = [t["exit_price"] for t in trades if t["exit_reason"] != "stop_loss"]
    stop_loss_exit_dates = [t["exit_date"] for t in trades if t["exit_reason"] == "stop_loss"]
    stop_loss_exit_prices = [t["exit_price"] for t in trades if t["exit_reason"] == "stop_loss"]

    ax_price.scatter(entry_dates, entry_prices, marker="^", color="green", label="entry", zorder=5)
    ax_price.scatter(normal_exit_dates, normal_exit_prices, marker="v", color="red", label="exit", zorder=5)
    ax_price.scatter(stop_loss_exit_dates, stop_loss_exit_prices, marker="v", color="darkred",
                      label="exit (stop_loss)", zorder=5)
    ax_price.set_title(f"{symbol} price + signals")
    ax_price.legend()

    ax_equity.plot(equity_curve.index, equity_curve.values, color="blue")
    ax_equity.set_title("Equity curve")

    fig.tight_layout()
    png_path = output_dir / f"{safe_symbol}_report.png"
    fig.savefig(png_path)
    plt.close(fig)

    metrics_path = output_dir / f"{safe_symbol}_metrics.txt"
    with open(metrics_path, "w") as f:
        for key, value in metrics.items():
            f.write(f"{key}: {value}\n")

    return png_path
