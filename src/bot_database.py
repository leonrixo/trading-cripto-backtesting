"""
bot_database.py: Base de datos SQLite persistente para registrar bots,
operaciones en tiempo real (trades) y curvas de capital (equity snapshots).
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "trading_records.db"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None):
    """Crea las tablas de base de datos si no existen."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Tabla de bots
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bots (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        bot_type TEXT NOT NULL,       -- 'grid' o 'scalping_1h'
        symbol TEXT NOT NULL,         -- ej. 'SOL/USDT'
        allocated_capital REAL NOT NULL,
        status TEXT NOT NULL,         -- 'running', 'paused', 'stopped'
        params_json TEXT,             -- JSON de parámetros específicos
        realized_profit REAL DEFAULT 0.0,
        unrealized_pnl REAL DEFAULT 0.0,
        total_trades INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # Tabla de operaciones (trades ejecutados en Testnet/Real)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id TEXT NOT NULL,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,           -- 'buy' o 'sell'
        price REAL NOT NULL,
        qty REAL NOT NULL,
        cost REAL NOT NULL,
        profit REAL DEFAULT 0.0,
        order_id_exchange TEXT,
        executed_at TEXT NOT NULL,
        FOREIGN KEY (bot_id) REFERENCES bots (id)
    );
    """)

    # Tabla de instantáneas de capital (para graficar la curva en el tiempo)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS equity_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        total_equity REAL NOT NULL,
        realized_profit REAL NOT NULL,
        FOREIGN KEY (bot_id) REFERENCES bots (id)
    );
    """)

    conn.commit()
    conn.close()


def create_bot(
    bot_id: str,
    name: str,
    bot_type: str,
    symbol: str,
    allocated_capital: float,
    params: Dict[str, Any],
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    params_str = json.dumps(params)

    with conn:
        conn.execute(
            """
            INSERT INTO bots (id, name, bot_type, symbol, allocated_capital, status, params_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'running', ?, ?, ?)
            """,
            (bot_id, name, bot_type, symbol, allocated_capital, params_str, now, now),
        )
    conn.close()
    return get_bot(bot_id, db_path)


def get_bot(bot_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bots WHERE id = ?", (bot_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    d["params"] = json.loads(d["params_json"]) if d["params_json"] else {}
    return d


def list_bots(status: Optional[str] = None, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    if status:
        cursor.execute("SELECT * FROM bots WHERE status = ? ORDER BY created_at DESC", (status,))
    else:
        cursor.execute("SELECT * FROM bots ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        d["params"] = json.loads(d["params_json"]) if d["params_json"] else {}
        result.append(d)
    return result


def update_bot_status(bot_id: str, status: str, db_path: Optional[Path] = None):
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute(
            "UPDATE bots SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, bot_id),
        )
    conn.close()


def record_trade(
    bot_id: str,
    symbol: str,
    side: str,
    price: float,
    qty: float,
    cost: float,
    profit: float = 0.0,
    order_id_exchange: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> int:
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()

    with conn:
        cursor = conn.execute(
            """
            INSERT INTO trades (bot_id, symbol, side, price, qty, cost, profit, order_id_exchange, executed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (bot_id, symbol, side, price, qty, cost, profit, order_id_exchange, now),
        )
        trade_id = cursor.lastrowid

        # Actualizar acumulados del bot
        conn.execute(
            """
            UPDATE bots 
            SET realized_profit = realized_profit + ?,
                total_trades = total_trades + 1,
                updated_at = ?
            WHERE id = ?
            """,
            (profit, now, bot_id),
        )

        # Registrar snapshot de equity
        conn.execute(
            """
            INSERT INTO equity_snapshots (bot_id, timestamp, total_equity, realized_profit)
            SELECT id, ?, allocated_capital + realized_profit, realized_profit
            FROM bots WHERE id = ?
            """,
            (now, bot_id),
        )

    conn.close()
    return trade_id


def get_bot_trades(bot_id: str, limit: int = 50, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM trades WHERE bot_id = ? ORDER BY id DESC LIMIT ?",
        (bot_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_bot_snapshots(bot_id: str, limit: int = 100, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM equity_snapshots WHERE bot_id = ? ORDER BY id ASC LIMIT ?",
        (bot_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_trades(limit: int = 50, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT t.*, b.name as bot_name, b.bot_type
        FROM trades t
        LEFT JOIN bots b ON t.bot_id = b.id
        ORDER BY t.id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

