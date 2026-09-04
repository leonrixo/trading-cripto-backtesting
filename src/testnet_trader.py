"""
testnet_trader.py: Conector oficial a Binance Testnet (Sandbox) usando ccxt.
Permite realizar pruebas con saldo virtual oficial sin arriesgar capital real.

Para obtener llaves gratuitas de Binance Testnet:
1. Entra con tu cuenta de GitHub en: https://testnet.binance.vision/
2. Haz clic en 'Generate HMAC_SHA256 Key'.
3. Copia el API Key y Secret Key en un archivo .env o variables de entorno:
   BINANCE_TESTNET_API_KEY=tu_api_key
   BINANCE_TESTNET_SECRET=tu_secret_key
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

import ccxt

# Cargar variables de entorno si existe archivo .env local
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def get_testnet_client(api_key: Optional[str] = None, secret: Optional[str] = None) -> ccxt.binance:
    """
    Crea una instancia de ccxt configurada en modo sandbox (Testnet de Binance).
    """
    key = os.getenv("BINANCE_TESTNET_API_KEY") if api_key is None else api_key
    sec = os.getenv("BINANCE_TESTNET_SECRET") if secret is None else secret


    exchange = ccxt.binance({
        "apiKey": key,
        "secret": sec,
        "enableRateLimit": True,
        "options": {
            "defaultType": "spot",
        },
    })
    # Activa la URL oficial de la Testnet (https://testnet.binance.vision)
    exchange.set_sandbox_mode(True)
    return exchange


def check_testnet_balance(exchange: Optional[ccxt.binance] = None) -> Dict[str, Any]:
    """
    Consulta los saldos disponibles en la cuenta de Testnet.
    Si no hay llaves configuradas, devuelve información explicativa.
    """
    if exchange is None:
        exchange = get_testnet_client()

    if not exchange.apiKey or not exchange.secret:
        return {
            "status": "missing_keys",
            "message": (
                "No se encontraron llaves de Testnet configuradas. "
                "Crea un archivo .env con BINANCE_TESTNET_API_KEY y BINANCE_TESTNET_SECRET. "
                "Puedes generarlas gratis en https://testnet.binance.vision/"
            ),
            "balances": {},
        }

    try:
        balance = exchange.fetch_balance()
        free_balances = {k: v for k, v in balance.get("free", {}).items() if v > 0}
        return {
            "status": "connected",
            "message": "Conexión exitosa con Binance Testnet",
            "balances": free_balances,
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Error al conectar con Binance Testnet: {exc}",
            "balances": {},
        }


def fetch_live_price(symbol: str = "BTC/USDT", exchange: Optional[ccxt.binance] = None) -> Dict[str, Any]:
    """
    Consulta el precio en vivo de una criptomoneda en Binance.
    """
    if exchange is None:
        exchange = get_testnet_client()

    ticker = exchange.fetch_ticker(symbol)
    return {
        "symbol": symbol,
        "last_price": ticker.get("last"),
        "bid": ticker.get("bid"),
        "ask": ticker.get("ask"),
        "timestamp": ticker.get("datetime"),
    }


def execute_paper_order(
    symbol: str,
    side: str,  # "buy" o "sell"
    amount: float,
    order_type: str = "market",
    price: Optional[float] = None,
    exchange: Optional[ccxt.binance] = None,
) -> Dict[str, Any]:
    """
    Envía una orden simulada oficial a la Testnet de Binance.
    Ajusta automáticamente la cantidad al tamaño de lote permitido por Binance.
    """
    if exchange is None:
        exchange = get_testnet_client()

    if not exchange.apiKey or not exchange.secret:
        raise ValueError("Se requieren API keys de Testnet para ejecutar órdenes.")

    if exchange.markets is None or symbol not in exchange.markets:
        try:
            exchange.load_markets()
        except Exception:
            pass

    # Ajustar a la precisión requerida por el par en Binance
    try:
        formatted_amount = float(exchange.amount_to_precision(symbol, amount))
    except Exception:
        formatted_amount = amount

    order = exchange.create_order(
        symbol=symbol,
        type=order_type,
        side=side,
        amount=formatted_amount,
        price=price,
    )
    return order


if __name__ == "__main__":
    print("=== Conector Binance Testnet ===")
    res = check_testnet_balance()
    print("Estado:", res["status"])
    print("Mensaje:", res["message"])
    if res["balances"]:
        main_coins = ["USDT", "BTC", "ETH", "BNB", "SOL"]
        summary = {k: res["balances"][k] for k in main_coins if k in res["balances"]}
        print("Saldos principales disponibles:", summary)

    try:
        btc_price = fetch_live_price("BTC/USDT")
        print(f"Precio en vivo de {btc_price['symbol']}: ${btc_price['last_price']:,.2f} USDT")
    except Exception as e:
        print(f"No se pudo consultar el ticker en vivo: {e}")


