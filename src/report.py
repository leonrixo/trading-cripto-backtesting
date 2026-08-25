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
) -> Path:
    """
    df: output de strategy.generate_signals (columnas close, fast_ma, slow_ma, signal).
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

    entries = df.index[(df["signal"] == 1) & (df["signal"].shift(1).fillna(0) == 0)]
    exits = df.index[(df["signal"] == 0) & (df["signal"].shift(1).fillna(0) == 1)]
    ax_price.scatter(entries, df.loc[entries, "close"], marker="^", color="green", label="entry", zorder=5)
    ax_price.scatter(exits, df.loc[exits, "close"], marker="v", color="red", label="exit", zorder=5)
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
