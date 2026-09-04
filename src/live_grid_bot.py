"""
live_grid_bot.py: Bot de Malla (Grid Trading) en tiempo real conectado a Binance Testnet.
Monitorea el precio en vivo y ejecuta compras escalonadas en caídas y ventas en subidas.
"""

import time
import argparse
import numpy as np
from testnet_trader import get_testnet_client, fetch_live_price, execute_paper_order, check_testnet_balance


def start_live_grid(
    symbol: str = "SOL/USDT",
    num_grids: int = 10,
    capital_per_grid_usd: float = 12.0,  # Cumple el mínimo notional de Binance (>= $10 USD)
    lower_price: float = None,
    upper_price: float = None,
    check_interval_seconds: int = 10,
    max_iterations: int = 30,  # Límite de iteraciones para demostración o continuo
):
    print(f"\n========================================================")
    print(f"🚀 INICIANDO BOT DE MALLA EN VIVO · BINANCE TESTNET")
    print(f"Par: {symbol} | Rejillas: {num_grids} | Intervalo: {check_interval_seconds}s")
    print(f"========================================================\n")

    exchange = get_testnet_client()
    balance_info = check_testnet_balance(exchange)
    print(f"✅ Conectado a Binance Testnet con éxito.")
    print(f"💰 Saldo USDT disponible: ${balance_info['balances'].get('USDT', 0):,.2f} USDT")

    # 1. Obtener precio actual para calcular rango si no se especificó
    ticker = fetch_live_price(symbol, exchange)
    current_price = ticker["last_price"]
    print(f"📍 Precio actual de {symbol}: ${current_price:,.2f} USDT")

    if lower_price is None or lower_price <= 0:
        lower_price = round(current_price * 0.95, 2)  # -5%
    if upper_price is None or upper_price <= 0:
        upper_price = round(current_price * 1.05, 2)  # +5%

    prices = np.linspace(lower_price, upper_price, num_grids + 1)
    grid_levels = [round(float(p), 2) for p in prices]
    grid_step = (upper_price - lower_price) / num_grids

    print(f"🕸️ Rango de Malla: ${lower_price:,.2f} ── ${upper_price:,.2f} USDT")
    print(f"📏 Paso entre rejillas: ${grid_step:,.2f} USDT ({((grid_step/current_price)*100):.2f}%)")
    print(f"📋 Niveles de la Malla: {grid_levels}\n")

    # Inicializar estado de las ranuras de la malla
    slots = []
    for i in range(num_grids):
        buy_p = grid_levels[i]
        sell_p = grid_levels[i + 1]
        state = "waiting_buy" if current_price <= buy_p else "holding_sell"
        slots.append({
            "buy_price": buy_p,
            "sell_price": sell_p,
            "state": state,
            "entry_cost": current_price if state == "holding_sell" else 0.0,
        })

    realized_profit = 0.0
    iteration = 0

    print("🟢 Bot en ejecución vigilando el libro de órdenes en vivo...")
    print("Presiona Ctrl+C en cualquier momento para detener.\n")

    try:
        while True:
            iteration += 1
            ticker = fetch_live_price(symbol, exchange)
            price = ticker["last_price"]
            timestamp = ticker["timestamp"]

            print(f"[{timestamp[11:19]}] Ciclo #{iteration} | Precio {symbol}: ${price:,.2f} USDT", end="\r")

            # Chequeo de niveles
            for idx, slot in enumerate(slots):
                # Ocasión de COMPRA: el precio cayó hasta el nivel de compra
                if slot["state"] == "waiting_buy" and price <= slot["buy_price"]:
                    print(f"\n⚡ [EJECUCIÓN] Precio ${price:,.2f} tocó nivel inferior ${slot['buy_price']:,.2f}")
                    qty = round(capital_per_grid_usd / price, 3)
                    try:
                        order = execute_paper_order(symbol, "buy", qty, "market", exchange=exchange)
                        print(f"   🟢 COMPRA REALIZADA en Testnet! ID: {order['id']} | Qty: {qty} {symbol.split('/')[0]}")
                        slot["state"] = "holding_sell"
                        slot["entry_cost"] = price
                    except Exception as e:
                        print(f"   ⚠️ Error al enviar orden de compra: {e}")

                # Ocasión de VENTA (Toma de Beneficio): el precio subió al nivel superior
                elif slot["state"] == "holding_sell" and price >= slot["sell_price"]:
                    print(f"\n🎉 [BENEFICIO] Precio ${price:,.2f} tocó nivel superior ${slot['sell_price']:,.2f}")
                    qty = round(capital_per_grid_usd / slot["entry_cost"], 3)
                    try:
                        order = execute_paper_order(symbol, "sell", qty, "market", exchange=exchange)
                        profit = (price - slot["entry_cost"]) * qty
                        realized_profit += profit
                        print(f"   🔴 VENTA CON GANANCIA en Testnet! ID: {order['id']} | Ganancia: +${profit:,.3f} USDT")
                        print(f"   💧 Ganancia total acumulada por goteo: +${realized_profit:,.3f} USDT")
                        slot["state"] = "waiting_buy"
                        slot["entry_cost"] = 0.0
                    except Exception as e:
                        print(f"   ⚠️ Error al enviar orden de venta: {e}")

            if max_iterations and iteration >= max_iterations:
                print(f"\n🏁 Demostración completada ({max_iterations} ciclos completados).")
                break

            time.sleep(check_interval_seconds)

    except KeyboardInterrupt:
        print("\n🛑 Bot detenido por el usuario.")

    print(f"\nResumen final: Ganancia realizada: +${realized_profit:,.3f} USDT")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot de Malla en vivo para Binance Testnet")
    parser.add_argument("--symbol", default="SOL/USDT", help="Par cripto (ej. SOL/USDT, BTC/USDT)")
    parser.add_argument("--grids", type=int, default=10, help="Número de rejillas")
    parser.add_argument("--interval", type=int, default=5, help="Segundos entre chequeos")
    parser.add_argument("--cycles", type=int, default=6, help="Ciclos a ejecutar (0 para infinito)")
    args = parser.parse_args()

    start_live_grid(
        symbol=args.symbol,
        num_grids=args.grids,
        check_interval_seconds=args.interval,
        max_iterations=args.cycles,
    )

