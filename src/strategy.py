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
