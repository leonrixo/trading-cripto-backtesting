import pandas as pd
from strategy import generate_signals

def test_signal_goes_long_after_crossover_with_one_bar_lag():
    # Precio sube de forma sostenida: la media rápida (2) cruza arriba de la
    # lenta (4) en algún punto y la señal debe activarse UNA barra después.
    prices = [10, 10, 10, 10, 11, 12, 13, 14, 15, 16]
    df = pd.DataFrame({"close": prices})

    out = generate_signals(df, fast_window=2, slow_window=4)

    assert list(out.columns) >= ["fast_ma", "slow_ma", "signal"] or set(
        ["fast_ma", "slow_ma", "signal"]
    ).issubset(out.columns)
    # La primera barra siempre debe estar en 0 (no hay barra anterior).
    assert out["signal"].iloc[0] == 0
    # Donde fast_ma > slow_ma en t, signal debe ser 1 en t+1 (no en t).
    crossed_up = (out["fast_ma"] > out["slow_ma"])
    for t in range(1, len(out)):
        assert out["signal"].iloc[t] == int(bool(crossed_up.iloc[t - 1]))


def test_signal_returns_to_flat_after_crossunder():
    prices = [20, 19, 18, 17, 16, 15, 14, 13, 12, 11]
    df = pd.DataFrame({"close": prices})

    out = generate_signals(df, fast_window=2, slow_window=4)

    # Con precios cayendo, la media rápida termina por debajo de la lenta,
    # así que la señal final debe quedar en 0.
    assert out["signal"].iloc[-1] == 0
