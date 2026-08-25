import pandas as pd


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 10_000.0,
    stop_loss_pct: float = 0.05,
    position_size_pct: float = 1.0,
) -> dict:
    """
    df: debe tener columnas 'close' y 'signal' (0/1), como el output de
    strategy.generate_signals.
    Simula: entra largo cuando signal pasa a 1, sale cuando signal vuelve a 0
    o cuando el precio cae stop_loss_pct por debajo del precio de entrada
    (lo que ocurra primero).
    """
    cash = initial_capital
    position = 0.0
    entry_price = None
    entry_date = None
    equity = []
    trades = []

    for date, row in df.iterrows():
        price = row["close"]
        signal = row["signal"]

        if position == 0.0 and signal == 1:
            position = (cash * position_size_pct) / price
            cash -= position * price
            entry_price = price
            entry_date = date

        elif position > 0.0:
            stop_price = entry_price * (1 - stop_loss_pct)
            hit_stop = price <= stop_price
            if signal == 0 or hit_stop:
                cash += position * price
                pnl_pct = (price - entry_price) / entry_price
                trades.append({
                    "entry_date": entry_date,
                    "exit_date": date,
                    "entry_price": entry_price,
                    "exit_price": price,
                    "pnl_pct": pnl_pct,
                    "exit_reason": "stop_loss" if hit_stop else "signal",
                })
                position = 0.0
                entry_price = None
                entry_date = None

        equity.append(cash + position * price)

    # Force-close any open position at end of data
    if position > 0.0:
        last_date = df.index[-1]
        last_price = df.iloc[-1]["close"]
        cash += position * last_price
        pnl_pct = (last_price - entry_price) / entry_price
        trades.append({
            "entry_date": entry_date,
            "exit_date": last_date,
            "entry_price": entry_price,
            "exit_price": last_price,
            "pnl_pct": pnl_pct,
            "exit_reason": "end_of_data",
        })
        position = 0.0
        entry_price = None
        entry_date = None

    equity_curve = pd.Series(equity, index=df.index, name="equity")
    return {"equity_curve": equity_curve, "trades": trades}
