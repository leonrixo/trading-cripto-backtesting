"""
bot_manager.py: Orquestador central para ejecutar múltiples bots concurrentes
(Grid Trading y Scalping 1h) en segundo plano conectados a Binance Testnet.
"""

import time
import uuid
import threading
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

import ccxt
from bot_database import (
    init_db,
    create_bot,
    get_bot,
    list_bots,
    update_bot_status,
    record_trade,
    get_bot_trades,
    get_bot_snapshots,
    DEFAULT_DB_PATH,
)
from testnet_trader import get_testnet_client, fetch_live_price, execute_paper_order
from data import fetch_ohlcv
from strategy import generate_scalping_signals


class BotManager:
    """Administrador singleton de bots concurrentes."""

    def __init__(self, db_path: Optional[Path] = None, max_active_bots: int = 5):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.max_active_bots = max_active_bots
        self._lock = threading.Lock()
        self._threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._exchange = None

        init_db(self.db_path)

    @property
    def exchange(self) -> ccxt.binance:
        if self._exchange is None:
            self._exchange = get_testnet_client()
        return self._exchange

    def start_bot(
        self,
        bot_type: str,  # 'grid' o 'scalping_1h'
        symbol: str,    # ej. 'SOL/USDT', 'BTC/USDT'
        allocated_capital: float,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crea y enciende un nuevo bot en segundo plano."""
        params = params or {}

        # Validaciones básicas
        if bot_type not in ("grid", "scalping_1h"):
            raise ValueError(f"Tipo de bot no soportado: {bot_type}")
        if allocated_capital < 10.0:
            raise ValueError("El capital mínimo para operar en Binance es de $10 USDT.")

        with self._lock:
            active_count = sum(1 for e in self._stop_events.values() if not e.is_set())
            if active_count >= self.max_active_bots:
                raise ValueError(f"Límite alcanzado: máximo {self.max_active_bots} bots simultáneos.")

            # Generar ID único
            clean_sym = symbol.replace("/", "_")
            short_id = uuid.uuid4().hex[:6]
            bot_id = f"{bot_type}_{clean_sym}_{short_id}"
            name = f"{'Malla' if bot_type == 'grid' else 'Scalping 1h'} {symbol}"

            # Crear en base de datos
            bot_record = create_bot(
                bot_id=bot_id,
                name=name,
                bot_type=bot_type,
                symbol=symbol,
                allocated_capital=allocated_capital,
                params=params,
                db_path=self.db_path,
            )

            # Iniciar hilo trabajador
            stop_event = threading.Event()
            self._stop_events[bot_id] = stop_event

            if bot_type == "grid":
                target_fn = self._run_grid_worker
            else:
                target_fn = self._run_scalping_worker

            thread = threading.Thread(
                target=target_fn,
                args=(bot_id, symbol, allocated_capital, params, stop_event),
                daemon=True,
                name=f"Worker-{bot_id}",
            )
            self._threads[bot_id] = thread
            thread.start()

            return bot_record

    def stop_bot(self, bot_id: str) -> Dict[str, Any]:
        """Detiene la ejecución de un bot en vivo."""
        with self._lock:
            stop_event = self._stop_events.get(bot_id)
            if stop_event:
                stop_event.set()

            update_bot_status(bot_id, "stopped", db_path=self.db_path)
            bot = get_bot(bot_id, db_path=self.db_path)
            if not bot:
                raise ValueError(f"Bot {bot_id} no encontrado")
            return bot

    def get_bot_status(self, bot_id: str) -> Optional[Dict[str, Any]]:
        bot = get_bot(bot_id, db_path=self.db_path)
        if not bot:
            return None
        # Comprobar si el hilo sigue vivo
        thread = self._threads.get(bot_id)
        stop_event = self._stop_events.get(bot_id)
        is_alive = bool(thread and thread.is_alive() and stop_event and not stop_event.is_set())
        bot["is_thread_alive"] = is_alive
        return bot

    def list_all_bots(self) -> List[Dict[str, Any]]:
        bots = list_bots(db_path=self.db_path)
        for b in bots:
            thread = self._threads.get(b["id"])
            stop_event = self._stop_events.get(b["id"])
            b["is_thread_alive"] = bool(thread and thread.is_alive() and stop_event and not stop_event.is_set())
        return bots

    # ── Trabajador de Malla en Vivo ──────────────────────────────
    def _run_grid_worker(
        self,
        bot_id: str,
        symbol: str,
        capital: float,
        params: Dict[str, Any],
        stop_event: threading.Event,
    ):
        num_grids = int(params.get("num_grids", 10))
        check_interval = int(params.get("interval_seconds", 10))

        # Obtener precio inicial
        try:
            ticker = fetch_live_price(symbol, self.exchange)
            start_price = ticker["last_price"]
        except Exception:
            start_price = 100.0

        lower_price = float(params.get("lower_price") or round(start_price * 0.95, 2))
        upper_price = float(params.get("upper_price") or round(start_price * 1.05, 2))
        prices = np.linspace(lower_price, upper_price, num_grids + 1)
        grid_levels = [round(float(p), 2) for p in prices]
        capital_per_grid = capital / num_grids

        slots = []
        for i in range(num_grids):
            buy_p = grid_levels[i]
            sell_p = grid_levels[i + 1]
            state = "waiting_buy" if start_price <= buy_p else "holding_sell"
            slots.append({
                "buy_price": buy_p,
                "sell_price": sell_p,
                "state": state,
                "entry_cost": start_price if state == "holding_sell" else 0.0,
            })

        while not stop_event.is_set():
            try:
                ticker = fetch_live_price(symbol, self.exchange)
                price = float(ticker["last_price"])

                for slot in slots:
                    # Condición de compra
                    if slot["state"] == "waiting_buy" and price <= slot["buy_price"]:
                        qty = round(capital_per_grid / price, 4)
                        order_id = None
                        try:
                            order = execute_paper_order(symbol, "buy", qty, "market", exchange=self.exchange)
                            order_id = str(order.get("id"))
                        except Exception:
                            order_id = f"LOCAL_{int(time.time())}"

                        record_trade(
                            bot_id=bot_id,
                            symbol=symbol,
                            side="buy",
                            price=price,
                            qty=qty,
                            cost=price * qty,
                            profit=0.0,
                            order_id_exchange=order_id,
                            db_path=self.db_path,
                        )
                        slot["state"] = "holding_sell"
                        slot["entry_cost"] = price

                    # Condición de venta
                    elif slot["state"] == "holding_sell" and price >= slot["sell_price"]:
                        entry = slot["entry_cost"] or price
                        qty = round(capital_per_grid / entry, 4)
                        order_id = None
                        try:
                            order = execute_paper_order(symbol, "sell", qty, "market", exchange=self.exchange)
                            order_id = str(order.get("id"))
                        except Exception:
                            order_id = f"LOCAL_{int(time.time())}"

                        profit = (price - entry) * qty
                        record_trade(
                            bot_id=bot_id,
                            symbol=symbol,
                            side="sell",
                            price=price,
                            qty=qty,
                            cost=price * qty,
                            profit=profit,
                            order_id_exchange=order_id,
                            db_path=self.db_path,
                        )
                        slot["state"] = "waiting_buy"
                        slot["entry_cost"] = 0.0

            except Exception:
                pass

            stop_event.wait(check_interval)

    # ── Trabajador de Scalping 1h en Vivo ────────────────────────
    def _run_scalping_worker(
        self,
        bot_id: str,
        symbol: str,
        capital: float,
        params: Dict[str, Any],
        stop_event: threading.Event,
    ):
        check_interval = int(params.get("interval_seconds", 30))
        fast_win = int(params.get("fast_window", 9))
        slow_win = int(params.get("slow_window", 21))
        stop_loss_pct = float(params.get("stop_loss_pct", 0.02))

        position_qty = 0.0
        entry_price = 0.0

        while not stop_event.is_set():
            try:
                # Descargar velas recientes de 1h
                df = fetch_ohlcv(symbol, timeframe="1h", refresh=True)
                if len(df) >= slow_win:
                    df = generate_scalping_signals(df, fast_window=fast_win, slow_window=slow_win)
                    last_row = df.iloc[-1]
                    signal = int(last_row["signal"])
                    current_price = float(last_row["close"])

                    # Abrir posición larga
                    if position_qty == 0.0 and signal == 1:
                        qty = round(capital / current_price, 4)
                        order_id = None
                        try:
                            order = execute_paper_order(symbol, "buy", qty, "market", exchange=self.exchange)
                            order_id = str(order.get("id"))
                        except Exception:
                            order_id = f"LOCAL_{int(time.time())}"

                        record_trade(
                            bot_id=bot_id,
                            symbol=symbol,
                            side="buy",
                            price=current_price,
                            qty=qty,
                            cost=current_price * qty,
                            profit=0.0,
                            order_id_exchange=order_id,
                            db_path=self.db_path,
                        )
                        position_qty = qty
                        entry_price = current_price

                    # Cerrar posición (señal contraria o stop-loss 2%)
                    elif position_qty > 0.0:
                        hit_stop = current_price <= (entry_price * (1 - stop_loss_pct))
                        if signal == 0 or hit_stop:
                            order_id = None
                            try:
                                order = execute_paper_order(symbol, "sell", position_qty, "market", exchange=self.exchange)
                                order_id = str(order.get("id"))
                            except Exception:
                                order_id = f"LOCAL_{int(time.time())}"

                            profit = (current_price - entry_price) * position_qty
                            record_trade(
                                bot_id=bot_id,
                                symbol=symbol,
                                side="sell",
                                price=current_price,
                                qty=position_qty,
                                cost=current_price * position_qty,
                                profit=profit,
                                order_id_exchange=order_id,
                                db_path=self.db_path,
                            )
                            position_qty = 0.0
                            entry_price = 0.0

            except Exception:
                pass

            stop_event.wait(check_interval)
