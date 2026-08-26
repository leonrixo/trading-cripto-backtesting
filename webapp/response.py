import math


def _sanitize(value):
    if value is None:
        return None
    try:
        if not math.isfinite(value):
            return None
    except TypeError:
        pass
    return float(value)


def build_response(symbol: str, df, result: dict, metrics: dict, params: dict) -> dict:
    """
    df: output de strategy.generate_signals (columnas close, fast_ma, slow_ma).
    result: output de backtest.run_backtest ({"equity_curve": ..., "trades": [...]}).
    metrics: output de metrics.compute_metrics.
    params: dict plano de parámetros de la estrategia (fast_window, slow_window,
        stop_loss_pct, initial_capital); se pasa tal cual, sin sanitizar.
    Regresa un dict listo para serializar a JSON: fechas como strings ISO, NaN
    convertido a None (JSON no tiene NaN literal válido).
    """
    dates = [d.strftime("%Y-%m-%d") for d in df.index]
    close = [_sanitize(v) for v in df["close"]]
    fast_ma = [_sanitize(v) for v in df["fast_ma"]]
    slow_ma = [_sanitize(v) for v in df["slow_ma"]]
    equity_curve = [_sanitize(v) for v in result["equity_curve"]]

    trades = [
        {
            "entry_date": t["entry_date"].strftime("%Y-%m-%d"),
            "entry_price": _sanitize(t["entry_price"]),
            "exit_date": t["exit_date"].strftime("%Y-%m-%d"),
            "exit_price": _sanitize(t["exit_price"]),
            "pnl_pct": _sanitize(t["pnl_pct"]),
            "exit_reason": t["exit_reason"],
        }
        for t in result["trades"]
    ]

    metrics_out = {k: (v if k == "num_trades" else _sanitize(v)) for k, v in metrics.items()}

    return {
        "symbol": symbol,
        "dates": dates,
        "close": close,
        "fast_ma": fast_ma,
        "slow_ma": slow_ma,
        "equity_curve": equity_curve,
        "trades": trades,
        "metrics": metrics_out,
        "params": params,
    }
