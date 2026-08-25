# Backtesting cripto v1 - Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir un sistema de backtesting en Python para una estrategia de cruce de
medias móviles sobre BTC/USDT y ETH/USDT en timeframe diario, con reporte de métricas y
gráfica.

**Architecture:** Módulos Python puros y testeables (`strategy`, `backtest`, `metrics`)
que no tocan red ni disco, más dos módulos de "borde" (`data`, `report`) que sí lo hacen
pero aceptan inyección de dependencias/rutas para poder testearse sin red real ni
archivos reales. `main.py` orquesta todo para ambos símbolos.

**Tech Stack:** Python 3.11+, pandas, numpy, ccxt (datos de Binance), matplotlib
(gráficas), pytest (tests).

**Spec:** [PROYECTO.md](PROYECTO.md)

## Global Constraints

- Timeframe: velas diarias (1d).
- Símbolos v1: BTC/USDT y ETH/USDT.
- Sin API key / sin cuenta de exchange — solo datos públicos vía ccxt.
- Sin frameworks de backtesting externos (backtrader/vectorbt quedan fuera de la v1).
- Todas las funciones de lógica de negocio (`strategy.py`, `backtest.py`, `metrics.py`)
  deben ser puras (sin I/O) para poder testearse con datos sintéticos.

---

### Task 1: Estructura del proyecto y entorno

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `tests/conftest.py`
- Create: `src/__init__.py` (vacío, solo para que las herramientas reconozcan la carpeta)

**Interfaces:**
- Produces: `src/` en el `sys.path` de pytest (vía `conftest.py`), para que
  `tests/test_*.py` puedan hacer `import strategy`, `import backtest`, etc. sin empaquetar
  nada.

- [ ] **Step 1: Crear `requirements.txt`**

```
pandas>=2.0
numpy>=1.24
ccxt>=4.0
matplotlib>=3.7
pytest>=7.4
```

- [ ] **Step 2: Crear `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
data/*.csv
reports/*.png
reports/*.txt
```

- [ ] **Step 3: Crear `tests/conftest.py`**

```python
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
```

- [ ] **Step 4: Crear `src/__init__.py` vacío**

Archivo vacío (0 bytes).

- [ ] **Step 5: Inicializar git e instalar dependencias**

Run:
```bash
cd "Visual studio claude/trading-cripto-backtesting"
git init
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
```

Expected: el entorno virtual se crea y las dependencias se instalan sin errores.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .gitignore tests/conftest.py src/__init__.py PROYECTO.md PLAN.md
git commit -m "chore: project scaffolding"
```

---

### Task 2: Módulo de estrategia (cruce de medias móviles)

**Files:**
- Create: `src/strategy.py`
- Test: `tests/test_strategy.py`

**Interfaces:**
- Produces: `generate_signals(df: pd.DataFrame, fast_window: int, slow_window: int) -> pd.DataFrame`
  — recibe un DataFrame con columna `close` (indexado por fecha, orden ascendente) y
  regresa una copia con columnas nuevas: `fast_ma`, `slow_ma`, `signal` (0 o 1, sin
  look-ahead: la señal calculada en la barra `t` solo se activa desde la barra `t+1`).

- [ ] **Step 1: Escribir el test que debe fallar**

```python
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
```

- [ ] **Step 2: Correr el test y confirmar que falla**

Run: `pytest tests/test_strategy.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'strategy'`

- [ ] **Step 3: Implementar `src/strategy.py`**

```python
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
```

- [ ] **Step 4: Correr el test y confirmar que pasa**

Run: `pytest tests/test_strategy.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/strategy.py tests/test_strategy.py
git commit -m "feat: add moving average crossover signal generation"
```

---

### Task 3: Motor de backtest

**Files:**
- Create: `src/backtest.py`
- Test: `tests/test_backtest.py`

**Interfaces:**
- Consumes: DataFrame con columnas `close` y `signal` (como el que produce
  `generate_signals` de Task 2).
- Produces: `run_backtest(df, initial_capital=10_000.0, stop_loss_pct=0.05, position_size_pct=1.0) -> dict`
  con claves:
  - `"equity_curve"`: `pd.Series` indexada igual que `df`, valor del portafolio en cada barra.
  - `"trades"`: lista de dicts `{entry_date, exit_date, entry_price, exit_price, pnl_pct, exit_reason}`
    donde `exit_reason` es `"signal"` o `"stop_loss"`.

- [ ] **Step 1: Escribir el test que debe fallar**

```python
import pandas as pd
from backtest import run_backtest


def test_opens_and_closes_position_on_signal_change():
    df = pd.DataFrame({
        "close":  [100, 100, 110, 120, 120],
        "signal": [0,   1,   1,   1,   0],
    })

    result = run_backtest(df, initial_capital=1000.0, stop_loss_pct=0.5, position_size_pct=1.0)

    assert len(result["trades"]) == 1
    trade = result["trades"][0]
    assert trade["exit_reason"] == "signal"
    assert trade["entry_price"] == 100
    assert trade["exit_price"] == 120
    assert abs(trade["pnl_pct"] - 0.2) < 1e-9
    # El equity final debe reflejar la ganancia de 100 -> 120 (20%).
    assert abs(result["equity_curve"].iloc[-1] - 1200.0) < 1e-6


def test_stop_loss_closes_position_early():
    df = pd.DataFrame({
        "close":  [100, 100, 90, 80, 80],
        "signal": [0,   1,   1,  1,  1],
    })

    result = run_backtest(df, initial_capital=1000.0, stop_loss_pct=0.05, position_size_pct=1.0)

    assert len(result["trades"]) == 1
    assert result["trades"][0]["exit_reason"] == "stop_loss"
    # Con stop_loss_pct=0.05 sobre entrada de 100, debe salir en <= 95, o sea en la barra de 90.
    assert result["trades"][0]["exit_price"] == 90
```

- [ ] **Step 2: Correr el test y confirmar que falla**

Run: `pytest tests/test_backtest.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'backtest'`

- [ ] **Step 3: Implementar `src/backtest.py`**

```python
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

    equity_curve = pd.Series(equity, index=df.index, name="equity")
    return {"equity_curve": equity_curve, "trades": trades}
```

- [ ] **Step 4: Correr el test y confirmar que pasa**

Run: `pytest tests/test_backtest.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/backtest.py tests/test_backtest.py
git commit -m "feat: add backtest engine with stop-loss support"
```

---

### Task 4: Módulo de métricas

**Files:**
- Create: `src/metrics.py`
- Test: `tests/test_metrics.py`

**Interfaces:**
- Consumes: `equity_curve` (`pd.Series`) y `trades` (`list[dict]` con clave `pnl_pct`),
  igual que el output de `run_backtest` de Task 3.
- Produces: `compute_metrics(equity_curve, trades, periods_per_year=365) -> dict` con
  claves `total_return`, `win_rate`, `max_drawdown`, `sharpe_ratio`, `num_trades`.

- [ ] **Step 1: Escribir el test que debe fallar**

```python
import pandas as pd
from metrics import compute_metrics


def test_total_return_and_win_rate():
    equity_curve = pd.Series([1000, 1100, 1050, 1200])
    trades = [
        {"pnl_pct": 0.10},
        {"pnl_pct": -0.05},
        {"pnl_pct": 0.15},
    ]

    result = compute_metrics(equity_curve, trades)

    assert abs(result["total_return"] - 0.2) < 1e-6
    assert abs(result["win_rate"] - (2 / 3)) < 1e-6
    assert result["num_trades"] == 3


def test_max_drawdown_is_negative_when_equity_dips():
    equity_curve = pd.Series([1000, 1200, 900, 1300])

    result = compute_metrics(equity_curve, trades=[])

    # De pico 1200 a valle 900 es una caída del 25%.
    assert abs(result["max_drawdown"] - (-0.25)) < 1e-6
    assert result["win_rate"] == 0.0
```

- [ ] **Step 2: Correr el test y confirmar que falla**

Run: `pytest tests/test_metrics.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'metrics'`

- [ ] **Step 3: Implementar `src/metrics.py`**

```python
import numpy as np
import pandas as pd


def compute_metrics(equity_curve: pd.Series, trades: list, periods_per_year: int = 365) -> dict:
    """
    equity_curve: valor del portafolio a través del tiempo (output de run_backtest).
    trades: lista de dicts con clave 'pnl_pct' (output de run_backtest).
    """
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1

    if trades:
        wins = sum(1 for t in trades if t["pnl_pct"] > 0)
        win_rate = wins / len(trades)
    else:
        win_rate = 0.0

    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    max_drawdown = drawdown.min()

    period_returns = equity_curve.pct_change().dropna()
    if period_returns.std() > 0:
        sharpe_ratio = (period_returns.mean() / period_returns.std()) * np.sqrt(periods_per_year)
    else:
        sharpe_ratio = 0.0

    return {
        "total_return": total_return,
        "win_rate": win_rate,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "num_trades": len(trades),
    }
```

- [ ] **Step 4: Correr el test y confirmar que pasa**

Run: `pytest tests/test_metrics.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/metrics.py tests/test_metrics.py
git commit -m "feat: add performance metrics computation"
```

---

### Task 5: Módulo de datos (descarga y cache de velas)

**Files:**
- Create: `src/data.py`
- Test: `tests/test_data.py`

**Interfaces:**
- Produces: `fetch_ohlcv(symbol: str, timeframe: str = "1d", since_days: int = 730, exchange_id: str = "binance", fetch_fn=None, cache_dir=None) -> pd.DataFrame`
  con columnas `open`, `high`, `low`, `close`, `volume`, indexado por `timestamp`
  (datetime). `fetch_fn` y `cache_dir` son inyectables para poder testear sin red real
  ni tocar la carpeta `data/` real.

- [ ] **Step 1: Escribir el test que debe fallar**

```python
import pandas as pd
from data import fetch_ohlcv


def fake_fetch_fn(exchange, symbol, timeframe, since_ms, limit):
    # Simula 3 velas diarias con timestamps en milisegundos.
    base_ms = 1_700_000_000_000
    day_ms = 24 * 60 * 60 * 1000
    return [
        [base_ms + 0 * day_ms, 100, 105, 95, 102, 10.0],
        [base_ms + 1 * day_ms, 102, 108, 100, 106, 12.0],
        [base_ms + 2 * day_ms, 106, 110, 104, 108, 8.0],
    ]


def test_fetch_ohlcv_downloads_and_caches(tmp_path):
    df = fetch_ohlcv("BTC/USDT", fetch_fn=fake_fetch_fn, cache_dir=tmp_path)

    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 3
    assert (tmp_path / "BTC_USDT_1d.csv").exists()


def test_fetch_ohlcv_uses_cache_without_calling_fetch_fn(tmp_path):
    def fetch_fn_that_should_not_run(*args, **kwargs):
        raise AssertionError("fetch_fn no debió llamarse: se esperaba usar el cache")

    fetch_ohlcv("BTC/USDT", fetch_fn=fake_fetch_fn, cache_dir=tmp_path)
    df = fetch_ohlcv("BTC/USDT", fetch_fn=fetch_fn_that_should_not_run, cache_dir=tmp_path)

    assert len(df) == 3
```

- [ ] **Step 2: Correr el test y confirmar que falla**

Run: `pytest tests/test_data.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'data'`

- [ ] **Step 3: Implementar `src/data.py`**

```python
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
) -> pd.DataFrame:
    """
    Descarga velas OHLCV para `symbol` (ej. 'BTC/USDT') vía ccxt y las cachea en CSV.
    Si el cache ya existe, lo reutiliza en vez de volver a descargar.
    `fetch_fn` y `cache_dir` existen para poder inyectar dobles de prueba en tests.
    """
    cache_dir = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{symbol.replace('/', '_')}_{timeframe}.csv"

    if cache_path.exists():
        return pd.read_csv(cache_path, index_col=0, parse_dates=True)

    exchange = getattr(ccxt, exchange_id)()
    since_ms = exchange.milliseconds() - since_days * 24 * 60 * 60 * 1000

    if fetch_fn is None:
        fetch_fn = lambda ex, sym, tf, since, limit: ex.fetch_ohlcv(sym, tf, since=since, limit=limit)

    rows = fetch_fn(exchange, symbol, timeframe, since_ms, 1000)
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("timestamp")

    df.to_csv(cache_path)
    return df
```

- [ ] **Step 4: Correr el test y confirmar que pasa**

Run: `pytest tests/test_data.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/data.py tests/test_data.py
git commit -m "feat: add OHLCV data fetching with local CSV cache"
```

---

### Task 6: Módulo de reporte

**Files:**
- Create: `src/report.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `df` (output de `generate_signals`, Task 2), `equity_curve` (de
  `run_backtest`, Task 3), `metrics` (dict de `compute_metrics`, Task 4).
- Produces: `generate_report(df, equity_curve, metrics, symbol, output_dir) -> Path`
  (ruta al PNG generado). También escribe `<symbol>_metrics.txt` en `output_dir`.

- [ ] **Step 1: Escribir el test que debe fallar**

```python
import pandas as pd
from report import generate_report


def test_generate_report_creates_png_and_metrics_file(tmp_path):
    df = pd.DataFrame({
        "close":   [100, 102, 104, 103, 105],
        "fast_ma": [None, None, 102.0, 103.0, 104.0],
        "slow_ma": [None, None, None, None, 102.8],
        "signal":  [0, 0, 1, 1, 0],
    })
    equity_curve = pd.Series([1000, 1000, 1020, 1010, 1030])
    metrics = {"total_return": 0.03, "win_rate": 1.0, "max_drawdown": -0.01,
               "sharpe_ratio": 1.2, "num_trades": 1}

    png_path = generate_report(df, equity_curve, metrics, "BTC/USDT", tmp_path)

    assert png_path.exists()
    metrics_path = tmp_path / "BTC_USDT_metrics.txt"
    assert metrics_path.exists()
    content = metrics_path.read_text()
    assert "total_return" in content
```

- [ ] **Step 2: Correr el test y confirmar que falla**

Run: `pytest tests/test_report.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'report'`

- [ ] **Step 3: Implementar `src/report.py`**

```python
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def generate_report(
    df: pd.DataFrame,
    equity_curve: pd.Series,
    metrics: dict,
    symbol: str,
    output_dir,
) -> Path:
    """
    df: output de strategy.generate_signals (columnas close, fast_ma, slow_ma, signal).
    Guarda un PNG con precio+señales+equity curve, y un .txt con las métricas.
    Regresa la ruta al PNG.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_symbol = symbol.replace("/", "_")

    fig, (ax_price, ax_equity) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    ax_price.plot(df.index, df["close"], label="close", color="black", linewidth=1)
    ax_price.plot(df.index, df["fast_ma"], label="fast_ma", linewidth=1)
    ax_price.plot(df.index, df["slow_ma"], label="slow_ma", linewidth=1)

    entries = df.index[(df["signal"] == 1) & (df["signal"].shift(1).fillna(0) == 0)]
    exits = df.index[(df["signal"] == 0) & (df["signal"].shift(1).fillna(0) == 1)]
    ax_price.scatter(entries, df.loc[entries, "close"], marker="^", color="green", label="entry", zorder=5)
    ax_price.scatter(exits, df.loc[exits, "close"], marker="v", color="red", label="exit", zorder=5)
    ax_price.set_title(f"{symbol} price + signals")
    ax_price.legend()

    ax_equity.plot(equity_curve.index, equity_curve.values, color="blue")
    ax_equity.set_title("Equity curve")

    fig.tight_layout()
    png_path = output_dir / f"{safe_symbol}_report.png"
    fig.savefig(png_path)
    plt.close(fig)

    metrics_path = output_dir / f"{safe_symbol}_metrics.txt"
    with open(metrics_path, "w") as f:
        for key, value in metrics.items():
            f.write(f"{key}: {value}\n")

    return png_path
```

- [ ] **Step 4: Correr el test y confirmar que pasa**

Run: `pytest tests/test_report.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add src/report.py tests/test_report.py
git commit -m "feat: add PNG + metrics report generation"
```

---

### Task 7: Script principal y primera corrida real

**Files:**
- Create: `src/main.py`
- Modify: `PROYECTO.md` (sección "Estado actual" con los resultados de la primera corrida)

**Interfaces:**
- Consumes: `fetch_ohlcv` (Task 5), `generate_signals` (Task 2), `run_backtest`
  (Task 3), `compute_metrics` (Task 4), `generate_report` (Task 6).
- Produces: script ejecutable (`python src/main.py`) que corre BTC/USDT y ETH/USDT y
  deja los reportes en `reports/`.

- [ ] **Step 1: Implementar `src/main.py`**

```python
from pathlib import Path

from data import fetch_ohlcv
from strategy import generate_signals
from backtest import run_backtest
from metrics import compute_metrics
from report import generate_report

SYMBOLS = ["BTC/USDT", "ETH/USDT"]
FAST_WINDOW = 20
SLOW_WINDOW = 50
STOP_LOSS_PCT = 0.05
INITIAL_CAPITAL = 10_000.0


def run_for_symbol(symbol: str, output_dir: Path) -> dict:
    df = fetch_ohlcv(symbol)
    df = generate_signals(df, FAST_WINDOW, SLOW_WINDOW)
    result = run_backtest(df, initial_capital=INITIAL_CAPITAL, stop_loss_pct=STOP_LOSS_PCT)
    metrics = compute_metrics(result["equity_curve"], result["trades"])
    generate_report(df, result["equity_curve"], metrics, symbol, output_dir)
    return metrics


def main():
    output_dir = Path(__file__).resolve().parent.parent / "reports"
    for symbol in SYMBOLS:
        metrics = run_for_symbol(symbol, output_dir)
        print(f"{symbol}: {metrics}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Correr el sistema completo por primera vez**

Run:
```bash
cd "Visual studio claude/trading-cripto-backtesting"
.venv/Scripts/python src/main.py
```

Expected: se imprimen las métricas de BTC/USDT y ETH/USDT en la terminal, y aparecen 4
archivos nuevos en `reports/` (`BTC_USDT_report.png`, `BTC_USDT_metrics.txt`,
`ETH_USDT_report.png`, `ETH_USDT_metrics.txt`).

- [ ] **Step 3: Correr toda la suite de tests una vez más (regresión)**

Run: `pytest -v`
Expected: PASS (9 tests en total, entre Tasks 2-6)

- [ ] **Step 4: Documentar resultados en `PROYECTO.md`**

Actualizar la sección "Estado actual" de `PROYECTO.md` con las métricas obtenidas
(total_return, win_rate, max_drawdown, sharpe_ratio, num_trades) para BTC/USDT y
ETH/USDT, y marcar los "Próximos pasos" ya completados con `[x]`.

- [ ] **Step 5: Commit**

```bash
git add src/main.py PROYECTO.md reports/.gitkeep
git commit -m "feat: add main orchestration script and record first backtest results"
```

Nota: si `reports/` no tiene ningún archivo versionable (los PNG/TXT están en
`.gitignore`), crear un `reports/.gitkeep` vacío antes de este commit para que la
carpeta quede en el repo.
