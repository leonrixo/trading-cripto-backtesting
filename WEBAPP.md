# Interfaz web - Diseño (v1)

**TL;DR:** App web local (FastAPI + frontend HTML/CSS/JS a medida) para correr el
backtester existente desde el navegador, eligiendo el símbolo desde un menú, con
gráficas interactivas en vez de archivos PNG sueltos. No reemplaza el CLI (`src/main.py`
sigue funcionando igual); es una segunda forma de usar el mismo backend.

## Objetivo

Darle al sistema de backtesting una interfaz gráfica bonita y usable desde el
navegador, sin tener que tocar código para elegir qué símbolo probar.

## Alcance v1

- **Configurable desde la interfaz:** solo el símbolo, elegido de esta lista curada
  (pares spot USDT en Binance, top ~14 por market cap, fijada a mano en
  `webapp/symbols.py` — no hay lookup en vivo de market cap):
  `BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT, XRP/USDT, DOGE/USDT, ADA/USDT, TRX/USDT,
  AVAX/USDT, TON/USDT, LINK/USDT, DOT/USDT, MATIC/USDT, LTC/USDT`.
  Si al implementar algún par ya no cotiza en Binance, se reemplaza por otro
  equivalente — no es un requisito exacto, es una lista razonable de referencia.
  Ventanas de medias móviles (20/50),
  stop-loss (5%) y capital inicial ($10,000) quedan fijos, igual que en el CLI hoy —
  se reutilizan las mismas constantes de `src/main.py` para no duplicar los números.
- **Backend:** servidor FastAPI local (`webapp/server.py`) que reutiliza tal cual los
  módulos existentes (`src/data.py`, `src/strategy.py`, `src/backtest.py`,
  `src/metrics.py`) — cero cambios a esos archivos. Expone:
  - `GET /api/symbols` → lista de símbolos disponibles.
  - `POST /api/backtest {"symbol": "BTC/USDT"}` → corre el pipeline completo y
    regresa un JSON con: fechas, precios de cierre, medias rápida/lenta, la lista de
    operaciones (`trades`, igual forma que ya produce `run_backtest`), la curva de
    equity, y las métricas (igual forma que `compute_metrics`).
  - Sirve el frontend estático (`webapp/static/`) en `/`.
- **Frontend:** una sola pantalla — selector de símbolo, botón "Correr backtest",
  estado de carga, banner de error si algo falla (símbolo inválido, error de red al
  bajar datos de Binance), y al terminar: tarjetas de métricas + dos gráficas
  interactivas (Plotly.js vía CDN):
  1. Precio de cierre + media rápida + media lenta, con marcadores de entrada/salida
     coloreados por motivo (`signal` / `stop_loss` / `end_of_data`) — derivados de
     `trades`, no de la columna `signal` (mismo criterio que se corrigió en el reporte
     PNG del CLI, para no repetir ese error aquí).
  2. Curva de equity a través del tiempo.
- **No en v1** (documentado como próximo paso, no se construye ahora): parámetros de
  estrategia configurables desde la UI, comparar dos símbolos lado a lado, guardar
  histórico de corridas, autenticación (es una app local de un solo usuario).

## Por qué este enfoque

- Se descartó Streamlit por limitar demasiado el control visual — el pedido explícito
  era una interfaz "bonita", y Streamlit no da libertad real de diseño.
- FastAPI + HTML/CSS/JS a medida (sin React/build pipeline) porque es una sola pantalla
  con una sola acción; un framework de frontend completo sería sobre-ingeniería para
  este alcance.
- Los módulos de `src/` no cambian — la web app es un consumidor más de la misma lógica
  que ya usa el CLI, igual que `report.py` es hoy un consumidor separado de
  `run_backtest`/`compute_metrics`.

## Contrato de la API (para que backend y frontend se construyan en paralelo sin ambigüedad)

```
GET /api/symbols
→ 200 {"symbols": ["BTC/USDT", "ETH/USDT", ...]}

POST /api/backtest
Body: {"symbol": "BTC/USDT"}
→ 200 {
    "symbol": "BTC/USDT",
    "dates": ["2024-08-26", "2024-08-27", ...],       // ISO date strings, un valor por vela
    "close": [61234.5, ...],                           // mismo largo que dates
    "fast_ma": [null, null, ..., 61050.2, ...],        // null donde rolling() da NaN
    "slow_ma": [null, ..., 60800.1, ...],
    "equity_curve": [10000.0, 10000.0, 10120.4, ...],  // mismo largo que dates
    "trades": [
      {"entry_date": "2024-09-10", "entry_price": 60000.0,
       "exit_date": "2024-09-25", "exit_price": 57000.0,
       "pnl_pct": -0.05, "exit_reason": "stop_loss"},
      ...
    ],
    "metrics": {"total_return": 0.4866, "win_rate": 0.5556,
                "max_drawdown": -0.2363, "sharpe_ratio": 0.8868, "num_trades": 9}
  }
→ 400 {"detail": "símbolo no soportado"}          (símbolo fuera de la lista curada)
→ 502 {"detail": "no se pudo descargar datos de Binance: <detalle>"}  (fallo de red/ccxt)

(`detail` es la clave que usa `fastapi.HTTPException` por defecto, no `error` — el
frontend debe leer `detail`.)
```

NaN (de `rolling().mean()` en las primeras barras) nunca debe llegar como literal `NaN`
en el JSON — no es JSON válido y rompe `JSON.parse` en el navegador. Se convierte a
`null` antes de responder.

## Estructura de archivos

```
webapp/
  server.py       # FastAPI app: endpoints, sys.path a src/, monta static/
  symbols.py      # lista curada de símbolos soportados
  static/
    index.html
    style.css
    app.js
tests/
  test_webapp_symbols.py   # test del endpoint /api/symbols (TestClient)
  test_webapp_response.py  # test de la función pura que arma el JSON de /api/backtest
```

## Cómo correr (para documentar en PROYECTO.md al terminar)

```bash
.venv/Scripts/python.exe webapp/server.py
```
Abre `http://127.0.0.1:8000` en el navegador.
