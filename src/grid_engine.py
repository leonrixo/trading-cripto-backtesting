from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd


def run_grid_backtest(
    df: pd.DataFrame,
    lower_price: float,
    upper_price: float,
    num_grids: int = 10,
    initial_capital: float = 10_000.0,
    fee_pct: float = 0.001,  # 0.1% comisión estándar Binance Spot
    stop_loss_pct: Optional[float] = None,  # Si el precio cae X% por debajo del lower_price
) -> Dict[str, Any]:
    """
    Simula una estrategia de Grid Trading (Malla aritmética):
    - Divide el rango [lower_price, upper_price] en `num_grids` intervalos.
    - Compra en escalones inferiores y vende en escalones superiores.
    - Descuenta comisiones en cada ejecución.
    - Devuelve curva de equity, lista de operaciones, beneficio de malla realizado y niveles.
    """
    if lower_price >= upper_price:
        raise ValueError("lower_price debe ser menor que upper_price")
    if num_grids < 2:
        raise ValueError("num_grids debe ser al menos 2")

    prices = np.linspace(lower_price, upper_price, num_grids + 1)
    grid_levels = [round(float(p), 4) for p in prices]
    grid_step = (upper_price - lower_price) / num_grids

    # Capital asignado por nivel de compra
    capital_per_grid = initial_capital / num_grids

    first_price = float(df.iloc[0]["close"])
    cash = initial_capital
    crypto_held = 0.0
    trades = []
    realized_profit = 0.0

    # Estado de cada intervalo:
    # Cada casilla representa el intervalo entre grid_levels[i] y grid_levels[i+1]
    slots = []
    for i in range(num_grids):
        buy_lvl = grid_levels[i]
        sell_lvl = grid_levels[i + 1]
        lot_cash = capital_per_grid

        if first_price >= sell_lvl:
            # Precio por encima: esperando retroceso para comprar
            slots.append({
                "buy_price": buy_lvl,
                "sell_price": sell_lvl,
                "state": "waiting_buy",
                "qty": 0.0,
                "entry_cost": 0.0,
            })
        elif first_price <= buy_lvl:
            # Precio por debajo: esperando rebote o compra en dip
            slots.append({
                "buy_price": buy_lvl,
                "sell_price": sell_lvl,
                "state": "waiting_buy",
                "qty": 0.0,
                "entry_cost": 0.0,
            })
        else:
            # first_price está en medio: compramos crypto ahora a first_price para vender a sell_lvl
            qty = (lot_cash * (1 - fee_pct)) / first_price
            cash -= lot_cash
            crypto_held += qty
            slots.append({
                "buy_price": buy_lvl,
                "sell_price": sell_lvl,
                "state": "holding_sell",
                "qty": qty,
                "entry_cost": first_price,
            })

    equity = []
    stopped_out = False
    stop_price = lower_price * (1 - stop_loss_pct) if stop_loss_pct else None

    for date, row in df.iterrows():
        high = float(row.get("high", row["close"]))
        low = float(row.get("low", row["close"]))
        close = float(row["close"])

        if stopped_out:
            equity.append(cash)
            continue

        # Verificar stop-loss de seguridad
        if stop_price and low <= stop_price:
            if crypto_held > 0:
                sell_val = crypto_held * stop_price * (1 - fee_pct)
                cash += sell_val
                trades.append({
                    "date": str(date),
                    "type": "stop_loss_exit",
                    "price": stop_price,
                    "qty": crypto_held,
                    "profit": (stop_price - lower_price) * crypto_held,
                    "cash": cash,
                })
                crypto_held = 0.0
            stopped_out = True
            equity.append(cash)
            continue

        # Procesar órdenes de compra en caídas (low <= buy_price)
        for slot in slots:
            if slot["state"] == "waiting_buy" and low <= slot["buy_price"]:
                exec_price = slot["buy_price"]
                lot_cash = capital_per_grid
                if cash >= lot_cash:
                    qty = (lot_cash * (1 - fee_pct)) / exec_price
                    cash -= lot_cash
                    crypto_held += qty
                    slot["qty"] = qty
                    slot["entry_cost"] = exec_price
                    slot["state"] = "holding_sell"
                    trades.append({
                        "date": str(date),
                        "type": "grid_buy",
                        "price": exec_price,
                        "qty": qty,
                        "profit": 0.0,
                        "cash": cash,
                    })

        # Procesar órdenes de venta en subidas (high >= sell_price)
        for slot in slots:
            if slot["state"] == "holding_sell" and high >= slot["sell_price"]:
                exec_price = slot["sell_price"]
                qty = slot["qty"]
                sell_val = qty * exec_price * (1 - fee_pct)
                cash += sell_val
                crypto_held -= qty

                buy_cost = qty * slot["entry_cost"]
                trade_profit = sell_val - buy_cost
                realized_profit += trade_profit

                slot["qty"] = 0.0
                slot["entry_cost"] = 0.0
                slot["state"] = "waiting_buy"

                trades.append({
                    "date": str(date),
                    "type": "grid_sell",
                    "price": exec_price,
                    "qty": qty,
                    "profit": trade_profit,
                    "cash": cash,
                })

        current_equity = cash + (crypto_held * close)
        equity.append(current_equity)

    equity_curve = pd.Series(equity, index=df.index, name="equity")
    final_equity = equity[-1] if equity else initial_capital
    total_return = (final_equity - initial_capital) / initial_capital

    grid_sells = [t for t in trades if t["type"] == "grid_sell"]
    grid_buys = [t for t in trades if t["type"] == "grid_buy"]

    return {
        "equity_curve": equity_curve,
        "trades": trades,
        "realized_profit": realized_profit,
        "total_return": total_return,
        "final_equity": final_equity,
        "initial_capital": initial_capital,
        "num_grid_buys": len(grid_buys),
        "num_grid_sells": len(grid_sells),
        "grid_levels": grid_levels,
        "grid_step": grid_step,
        "stopped_out": stopped_out,
    }

