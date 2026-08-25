# Interfaz web v1 - Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar una app web local (FastAPI + frontend HTML/CSS/JS a medida) que corre
el backtester existente eligiendo el símbolo desde un menú, con gráficas interactivas.

**Architecture:** `webapp/server.py` reutiliza sin modificar los módulos de `src/`
(`data.py`, `strategy.py`, `backtest.py`, `metrics.py`) y expone dos endpoints REST.
`webapp/response.py` es una función pura que convierte los objetos de esos módulos en
JSON serializable (NaN→null). `webapp/static/` es el frontend, servido como archivos
estáticos por el mismo servidor.

**Tech Stack:** FastAPI, uvicorn, httpx (para TestClient en tests), Plotly.js (vía CDN,
sin build step) para las gráficas del frontend.

**Spec:** [WEBAPP.md](WEBAPP.md)

## Global Constraints

- No modificar `src/data.py`, `src/strategy.py`, `src/backtest.py`, `src/metrics.py` —
  la web app los consume tal cual.
- Único parámetro configurable desde la UI: el símbolo. Ventanas de medias (20/50),
  stop-loss (5%) y capital inicial ($10,000) se importan de `src/main.py`, no se
  duplican como constantes nuevas.
- Ningún literal `NaN` debe llegar en el JSON de respuesta — debe convertirse a `null`.
- Lista de símbolos fijada a mano en `webapp/symbols.py`:
  `BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT, XRP/USDT, DOGE/USDT, ADA/USDT, TRX/USDT,
  AVAX/USDT, TON/USDT, LINK/USDT, DOT/USDT, MATIC/USDT, LTC/USDT`.
- Este entorno no tiene herramientas de navegador (Playwright u otro) disponibles —
  cualquier verificación de frontend debe ser estructural (curl, lectura de código),
  nunca una captura de pantalla o interacción real de navegador. Decir explícitamente
  en el reporte que falta verificación visual humana, nunca afirmar que "se ve bien"
  sin haberlo visto.

---

### Task 1: Backend scaffolding — servidor FastAPI y endpoint de símbolos

**Files:**
- Modify: `requirements.txt` (agregar `fastapi`, `uvicorn[standard]`, `httpx`)
- Create: `webapp/symbols.py`
- Create: `webapp/server.py`
- Modify: `tests/conftest.py` (agregar `webapp/` a `sys.path`, igual que ya hace con `src/`)
- Test: `tests/test_webapp_symbols.py`

**Interfaces:**
- Produces: `app` (instancia de `FastAPI`) importable como `from server import app`;
  `GET /api/symbols` → `{"symbols": [...]}`.
- Produces: `SYMBOLS` (lista de 14 strings) en `webapp/symbols.py`, importable como
  `from symbols import SYMBOLS`.

- [ ] **Step 1: Agregar dependencias a `requirements.txt`**

```
pandas>=2.0
numpy>=1.24
ccxt>=4.0
matplotlib>=3.7
pytest>=7.4
fastapi>=0.115
uvicorn[standard]>=0.32
httpx>=0.27
```

- [ ] **Step 2: Crear `webapp/symbols.py`**

```python
SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT",
    "ADA/USDT", "TRX/USDT", "AVAX/USDT", "TON/USDT", "LINK/USDT", "DOT/USDT",
    "MATIC/USDT", "LTC/USDT",
]
```

- [ ] **Step 3: Modificar `tests/conftest.py` para agregar `webapp/` a `sys.path`**

Contenido completo del archivo (agrega el bloque de `webapp/` al ya existente de `src/`,
no lo reemplaza):

```python
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

WEBAPP_DIR = Path(__file__).resolve().parent.parent / "webapp"
if str(WEBAPP_DIR) not in sys.path:
    sys.path.insert(0, str(WEBAPP_DIR))
```

- [ ] **Step 4: Escribir el test que debe fallar**

```python
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_get_symbols_returns_curated_list():
    response = client.get("/api/symbols")
    assert response.status_code == 200
    data = response.json()
    assert "symbols" in data
    assert "BTC/USDT" in data["symbols"]
    assert "ETH/USDT" in data["symbols"]
    assert len(data["symbols"]) == 14
```

- [ ] **Step 5: Correr el test y confirmar que falla**

Run: `.venv/Scripts/python.exe -m pip install -r requirements.txt` (para instalar
fastapi/uvicorn/httpx), luego `.venv/Scripts/python.exe -m pytest tests/test_webapp_symbols.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'server'`

- [ ] **Step 6: Implementar `webapp/server.py`**

```python
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from symbols import SYMBOLS

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI()


@app.get("/api/symbols")
def get_symbols():
    return {"symbols": SYMBOLS}


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

Nota: `StaticFiles(directory=...)` falla al arrancar si el directorio no existe. Crea
`webapp/static/` con un archivo `index.html` mínimo de marcador de posición en este
mismo paso (una sola línea, `<!doctype html><title>placeholder</title>`) — Task 3 lo
reemplaza por completo.

- [ ] **Step 7: Correr el test y confirmar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_webapp_symbols.py -v`
Expected: PASS (1 test)

- [ ] **Step 8: Commit**

```bash
git add requirements.txt webapp/symbols.py webapp/server.py webapp/static/index.html tests/conftest.py tests/test_webapp_symbols.py
git commit -m "feat: add FastAPI server scaffolding and symbols endpoint"
```

---

### Task 2: Endpoint de backtest y función pura de armado de respuesta

**Files:**
- Create: `webapp/response.py`
- Modify: `webapp/server.py`
- Test: `tests/test_webapp_response.py`
- Test: `tests/test_webapp_backtest.py`

**Interfaces:**
- Consumes: `generate_signals` (Task 2 del plan original, `src/strategy.py`),
  `run_backtest` (`src/backtest.py`), `compute_metrics` (`src/metrics.py`),
  `fetch_ohlcv` (`src/data.py`), y las constantes `FAST_WINDOW`, `SLOW_WINDOW`,
  `STOP_LOSS_PCT`, `INITIAL_CAPITAL` ya definidas en `src/main.py`.
- Produces: `build_response(symbol: str, df, result: dict, metrics: dict) -> dict` en
  `webapp/response.py` — función pura (sin I/O), usada por el endpoint.
- Produces: `POST /api/backtest` en `webapp/server.py`.

- [ ] **Step 1: Escribir el test que debe fallar (función pura `build_response`)**

```python
import pandas as pd
from response import build_response


def test_build_response_sanitizes_nan_and_shapes_output():
    df = pd.DataFrame(
        {
            "close": [100.0, 102.0, 104.0],
            "fast_ma": [float("nan"), 101.0, 103.0],
            "slow_ma": [float("nan"), float("nan"), 102.0],
        },
        index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
    )
    result = {
        "equity_curve": pd.Series([1000.0, 1010.0, 1020.0], index=df.index),
        "trades": [
            {
                "entry_date": pd.Timestamp("2024-01-01"),
                "entry_price": 100.0,
                "exit_date": pd.Timestamp("2024-01-03"),
                "exit_price": 104.0,
                "pnl_pct": 0.04,
                "exit_reason": "signal",
            }
        ],
    }
    metrics = {
        "total_return": 0.02,
        "win_rate": 1.0,
        "max_drawdown": 0.0,
        "sharpe_ratio": 1.5,
        "num_trades": 1,
    }

    response = build_response("BTC/USDT", df, result, metrics)

    assert response["symbol"] == "BTC/USDT"
    assert response["dates"] == ["2024-01-01", "2024-01-02", "2024-01-03"]
    assert response["close"] == [100.0, 102.0, 104.0]
    assert response["fast_ma"][0] is None
    assert response["fast_ma"][1] == 101.0
    assert response["slow_ma"][1] is None
    assert response["equity_curve"] == [1000.0, 1010.0, 1020.0]
    assert response["trades"] == [
        {
            "entry_date": "2024-01-01",
            "entry_price": 100.0,
            "exit_date": "2024-01-03",
            "exit_price": 104.0,
            "pnl_pct": 0.04,
            "exit_reason": "signal",
        }
    ]
    assert response["metrics"]["num_trades"] == 1
    assert response["metrics"]["total_return"] == 0.02
```

- [ ] **Step 2: Correr el test y confirmar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_webapp_response.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'response'`

- [ ] **Step 3: Implementar `webapp/response.py`**

```python
import math


def _sanitize(value):
    if value is None:
        return None
    try:
        if math.isnan(value):
            return None
    except TypeError:
        pass
    return float(value)


def build_response(symbol: str, df, result: dict, metrics: dict) -> dict:
    """
    df: output de strategy.generate_signals (columnas close, fast_ma, slow_ma).
    result: output de backtest.run_backtest ({"equity_curve": ..., "trades": [...]}).
    metrics: output de metrics.compute_metrics.
    Regresa un dict listo para serializar a JSON: fechas como strings ISO, NaN
    convertido a None (JSON no tiene NaN literal válido).
    """
    dates = [d.strftime("%Y-%m-%d") for d in df.index]
    close = [_sanitize(v) for v in df["close"]]
    fast_ma = [_sanitize(v) for v in df["fast_ma"]]
    slow_ma = [_sanitize(v) for v in df["slow_ma"]]
    equity_curve = [_sanitize(v) for v in result["equity_curve"]]

    trades = [
        {
            "entry_date": t["entry_date"].strftime("%Y-%m-%d"),
            "entry_price": float(t["entry_price"]),
            "exit_date": t["exit_date"].strftime("%Y-%m-%d"),
            "exit_price": float(t["exit_price"]),
            "pnl_pct": float(t["pnl_pct"]),
            "exit_reason": t["exit_reason"],
        }
        for t in result["trades"]
    ]

    metrics_out = {k: (v if k == "num_trades" else _sanitize(v)) for k, v in metrics.items()}

    return {
        "symbol": symbol,
        "dates": dates,
        "close": close,
        "fast_ma": fast_ma,
        "slow_ma": slow_ma,
        "equity_curve": equity_curve,
        "trades": trades,
        "metrics": metrics_out,
    }
```

- [ ] **Step 4: Correr el test y confirmar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_webapp_response.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Escribir el test del endpoint que debe fallar (caso de símbolo inválido, sin red)**

```python
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_backtest_rejects_unsupported_symbol():
    response = client.post("/api/backtest", json={"symbol": "FAKE/USDT"})
    assert response.status_code == 400
```

- [ ] **Step 6: Correr el test y confirmar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_webapp_backtest.py -v`
Expected: FAIL (404, la ruta `/api/backtest` todavía no existe)

- [ ] **Step 7: Implementar el endpoint en `webapp/server.py`**

Agregar estos imports y esta ruta al archivo existente (no reemplazar lo del Task 1):

```python
from fastapi import HTTPException
from pydantic import BaseModel

from data import fetch_ohlcv
from strategy import generate_signals
from backtest import run_backtest
from metrics import compute_metrics
from main import FAST_WINDOW, SLOW_WINDOW, STOP_LOSS_PCT, INITIAL_CAPITAL
from response import build_response


class BacktestRequest(BaseModel):
    symbol: str


@app.post("/api/backtest")
def post_backtest(request: BacktestRequest):
    if request.symbol not in SYMBOLS:
        raise HTTPException(status_code=400, detail="símbolo no soportado")

    try:
        df = fetch_ohlcv(request.symbol)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"no se pudo descargar datos de Binance: {exc}",
        )

    df = generate_signals(df, FAST_WINDOW, SLOW_WINDOW)
    result = run_backtest(df, initial_capital=INITIAL_CAPITAL, stop_loss_pct=STOP_LOSS_PCT)
    metrics = compute_metrics(result["equity_curve"], result["trades"])

    return build_response(request.symbol, df, result, metrics)
```

Este bloque debe ir ANTES de la línea `app.mount("/", StaticFiles(...))` del Task 1 —
FastAPI resuelve rutas en orden de declaración, y el mount de archivos estáticos en
`/` no debe interceptar `/api/*`.

- [ ] **Step 8: Correr el test y confirmar que pasa**

Run: `.venv/Scripts/python.exe -m pytest tests/test_webapp_backtest.py tests/test_webapp_response.py -v`
Expected: PASS (2 tests)

- [ ] **Step 9: Commit**

```bash
git add webapp/response.py webapp/server.py tests/test_webapp_response.py tests/test_webapp_backtest.py
git commit -m "feat: add /api/backtest endpoint and response-building function"
```

---

### Task 3: Frontend (delegar a un agente de diseño de UI)

**Files:**
- Create: `webapp/static/index.html` (reemplaza el placeholder del Task 1)
- Create: `webapp/static/style.css`
- Create: `webapp/static/app.js`

**Interfaces:**
- Consumes: `GET /api/symbols` → `{"symbols": [...]}`.
- Consumes: `POST /api/backtest {"symbol": "..."}` → ver el contrato JSON completo en
  [WEBAPP.md](WEBAPP.md), sección "Contrato de la API". En caso de error: status 400 o
  502 con body `{"detail": "<mensaje>"}` (FastAPI usa la clave `detail`, no `error`,
  para `HTTPException` — ajustar el frontend a `detail`, no a `error` como decía el
  borrador inicial del contrato en WEBAPP.md).

**Diseño libre, requisitos funcionales fijos:**

Esta tarea SÍ tiene libertad de diseño visual completa (colores, tipografía, layout,
espaciado) — es exactamente lo que se está delegando a un agente de diseño de UI. Lo
que NO es negociable es el comportamiento funcional:

1. Al cargar la página: hacer `fetch('/api/symbols')` y llenar un `<select>` con una
   `<option>` por símbolo recibido.
2. Un botón dispara la corrida: al hacer click, deshabilitar el botón, mostrar un
   estado de carga visible, y hacer `fetch('/api/backtest', {method: 'POST', ...})`
   con `{"symbol": <valor del select>}` como body JSON
   (`headers: {'Content-Type': 'application/json'}`).
3. Si la respuesta es 200: ocultar el estado de carga y cualquier error previo, y
   mostrar:
   - Tarjetas de métricas: `total_return`, `win_rate` y `max_drawdown` como
     porcentaje (ej. "48.7%" — multiplicar por 100 y redondear a 1 decimal),
     `sharpe_ratio` como número con 2 decimales, `num_trades` como entero.
   - Una gráfica de Plotly.js con: línea de `close`, línea de `fast_ma`, línea de
     `slow_ma`, todas sobre el eje X de `dates`; además marcadores de dispersión para
     las entradas (`trades[].entry_date`/`entry_price`) y las salidas
     (`trades[].exit_date`/`exit_price`) — las salidas con `exit_reason == "stop_loss"`
     deben verse visualmente distintas de las demás salidas (otro color, por ejemplo).
   - Una segunda gráfica de Plotly.js con una sola línea: `equity_curve` sobre `dates`.
4. Si la respuesta NO es 200 (400/502), o si el `fetch` mismo falla (sin red): mostrar
   un banner de error visible con el mensaje del campo `detail` del cuerpo de la
   respuesta (o un mensaje genérico si el fetch falló antes de tener respuesta),
   ocultar el estado de carga, y NO mostrar gráficas ni métricas de una corrida
   anterior mezcladas con el error.
5. Sin build step: HTML plano con `<script src="app.js">` y
   `<link rel="stylesheet" href="style.css">`. Plotly.js vía CDN:
   `<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>` en el `<head>`.

Los IDs de elementos HTML son decisión tuya — como el mismo archivo de este Task
escribe HTML, CSS y JS juntos, solo tienen que ser consistentes entre sí.

- [ ] **Step 1: Implementar `index.html`, `style.css`, `app.js`** siguiendo los
      requisitos funcionales de arriba, con el diseño visual que consideres mejor.

- [ ] **Step 2: Verificación estructural (este entorno no tiene navegador disponible)**

Arrancar el servidor en segundo plano y verificar con `curl` que los archivos se
sirven correctamente:

```bash
.venv/Scripts/python.exe webapp/server.py &
sleep 2
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/style.css
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/app.js
kill %1
```

Expected: los tres devuelven `200`. Además, releer tu propio `app.js` en busca de
errores de sintaxis obvios (llaves/paréntesis balanceados, comillas cerradas) ya que
no hay forma de ejecutarlo en un navegador real desde aquí.

**Reporta explícitamente que la verificación visual real (abrir esto en un navegador
y ver que se ve bien, que las gráficas se dibujan, que los colores/tipografía se ven
como se pretende) queda pendiente para un humano — no afirmes que "se ve bien" sin
haberlo visto.**

- [ ] **Step 3: Commit**

```bash
git add webapp/static/index.html webapp/static/style.css webapp/static/app.js
git commit -m "feat: add frontend UI for the backtesting web app"
```

---

### Task 4: Verificación real end-to-end y documentación

**Files:**
- Modify: `PROYECTO.md` (agregar sección "Interfaz web")

**Interfaces:**
- Consumes: el servidor completo de `webapp/server.py` (Tasks 1-3), corriendo de verdad
  contra la red real de Binance.

- [ ] **Step 1: Correr el servidor real y probar ambos endpoints con curl**

```bash
cd "Visual studio claude/trading-cripto-backtesting"
.venv/Scripts/python.exe webapp/server.py &
sleep 2
curl -s http://127.0.0.1:8000/api/symbols
curl -s -X POST http://127.0.0.1:8000/api/backtest -H "Content-Type: application/json" -d "{\"symbol\": \"BTC/USDT\"}" > backtest_response.tmp.json
cat backtest_response.tmp.json | head -c 500
kill %1
```

Expected: `/api/symbols` regresa los 14 símbolos; `/api/backtest` regresa 200 con las
claves `symbol`, `dates`, `close`, `fast_ma`, `slow_ma`, `equity_curve`, `trades`,
`metrics`.

- [ ] **Step 2: Confirmar que no hay literales `NaN` en la respuesta**

```bash
grep -o "NaN" backtest_response.tmp.json | wc -l
```

Expected: `0` — si aparece cualquier `NaN`, el saneo de `build_response` tiene un
hueco (por ejemplo, un campo del dict de métricas que no pasó por `_sanitize`) y hay
que corregirlo antes de continuar. Borra `backtest_response.tmp.json` una vez
verificado (es un archivo temporal, no debe quedar en el repo).

- [ ] **Step 3: Actualizar `PROYECTO.md`**

Agregar una sección nueva (después de "## Estado actual", antes de "## Próximos
pasos"):

```markdown
## Interfaz web

Además del CLI (`src/main.py`), hay una interfaz web local para correr el backtester
eligiendo el símbolo desde un menú, con gráficas interactivas. Ver
[WEBAPP.md](WEBAPP.md) para el diseño completo.

Para correrla:

```bash
.venv/Scripts/python.exe webapp/server.py
```

Y abrir `http://127.0.0.1:8000` en el navegador.
```

- [ ] **Step 4: Correr toda la suite de tests una vez más (regresión)**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: PASS (todos los tests existentes más los 3 nuevos de esta plan: symbols,
response, backtest — 18 en total)

- [ ] **Step 5: Commit**

```bash
git add PROYECTO.md
git commit -m "docs: document the web interface and verify it end-to-end"
```
