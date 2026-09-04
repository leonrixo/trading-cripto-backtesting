from datetime import datetime, timezone
from pathlib import Path

import ccxt
import pandas as pd

DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / "data"


def fetch_ohlcv(
    symbol: str,
    timeframe: str = "1d",
    since_days: int = 730,
    exchange_id: str = "binance",
    fetch_fn=None,
    cache_dir=None,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    Descarga velas OHLCV para `symbol` (ej. 'BTC/USDT') vía ccxt y las cachea en CSV.
    Si el cache ya existe, lo reutiliza en vez de volver a descargar (salvo que
    `refresh=True`, que fuerza una nueva descarga e ignora el cache existente).
    `fetch_fn` y `cache_dir` existen para poder inyectar dobles de prueba en tests.
    """
    cache_dir = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{symbol.replace('/', '_')}_{timeframe}.csv"

    if cache_path.exists() and not refresh:
        return pd.read_csv(cache_path, index_col=0, parse_dates=True)

    exchange = getattr(ccxt, exchange_id)()
    effective_days = min(since_days, 40) if timeframe == "1h" and since_days == 730 else since_days
    since_ms = exchange.milliseconds() - effective_days * 24 * 60 * 60 * 1000

    if fetch_fn is None:
        fetch_fn = lambda ex, sym, tf, since, limit: ex.fetch_ohlcv(sym, tf, since=since, limit=limit)

    rows = fetch_fn(exchange, symbol, timeframe, since_ms, 1000)
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("timestamp")

    # La última vela puede seguir en formación; la descartamos antes de escribir el cache.
    now_utc = datetime.now(timezone.utc)
    if len(df) > 0:
        last_dt = df.index[-1]
        if timeframe == "1d":
            today_utc = now_utc.date()
            if last_dt.date() == today_utc:
                df = df.iloc[:-1]
        elif timeframe == "1h":
            current_hour_utc = now_utc.replace(minute=0, second=0, microsecond=0, tzinfo=None)
            if last_dt >= current_hour_utc:
                df = df.iloc[:-1]

    df.to_csv(cache_path)
    return df

