import pandas as pd


def generate_signals(df: pd.DataFrame, fast_window: int, slow_window: int) -> pd.DataFrame:
    """
    df: DataFrame con columna 'close', indexado y ordenado ascendentemente por fecha.
    Regresa una copia con columnas 'fast_ma', 'slow_ma' y 'signal' (0/1).
    La señal usa shift(1): un cruce detectado en la barra t solo aplica desde t+1,
    para no usar información del futuro (look-ahead bias).
    """
    out = df.copy()
    out["fast_ma"] = out["close"].rolling(window=fast_window).mean()
    out["slow_ma"] = out["close"].rolling(window=slow_window).mean()
    raw_signal = (out["fast_ma"] > out["slow_ma"]).astype(int)
    out["signal"] = raw_signal.shift(1).fillna(0).astype(int)
    return out


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calcula el Índice de Fuerza Relativa (RSI) clásico de Wilder.
    Rango de 0 a 100.
    """
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0.0, 1e-9)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def generate_scalping_signals(
    df: pd.DataFrame,
    fast_window: int = 9,
    slow_window: int = 21,
    rsi_period: int = 14,
    rsi_min: float = 40.0,
    rsi_max: float = 70.0,
) -> pd.DataFrame:
    """
    Estrategia de Scalping/Momentum (adecuada para velas de 1h):
    - Filtro de tendencia: Media rápida (ej. 9) > Media lenta (ej. 21).
    - Filtro de impulso: RSI en zona constructiva (rsi_min <= rsi <= rsi_max),
      evitando comprar cuando ya está en sobrecompra extrema (>70).
    - Sin look-ahead bias: señal retrasada por 1 vela (shift(1)).
    """
    out = df.copy()
    out["fast_ma"] = out["close"].rolling(window=fast_window).mean()
    out["slow_ma"] = out["close"].rolling(window=slow_window).mean()
    out["rsi"] = compute_rsi(out["close"], period=rsi_period)

    ma_bullish = out["fast_ma"] > out["slow_ma"]
    rsi_valid = (out["rsi"] >= rsi_min) & (out["rsi"] <= rsi_max)
    raw_signal = (ma_bullish & rsi_valid).astype(int)

    out["signal"] = raw_signal.shift(1).fillna(0).astype(int)
    return out

