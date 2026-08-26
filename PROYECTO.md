# Trading cripto - Sistema de backtesting

**TL;DR:** Sistema en Python para probar (backtestear) estrategias de trading en cripto
sobre datos históricos, antes de arriesgar dinero real. v1: cruce de medias móviles,
timeframe diario, 14 pares cripto/USDT en Binance. Tiene un CLI (`src/main.py`, corre
BTC/ETH fijos) y una interfaz web local (`webapp/`, símbolo elegible desde un menú,
gráficas interactivas) — ambos funcionando y corridos contra datos reales de Binance.
Pendiente: nadie ha abierto la interfaz web en un navegador todavía (ver "Pendientes").

## Objetivo

Construir un sistema propio y transparente para cuantificar estrategias de trading en
cripto, empezando por backtesting (no trading en vivo todavía). Inspirado en la idea de
que herramientas como Claude Code permiten a un trader retail construir y probar sistemas
que antes solo estaban al alcance de fondos/instituciones.

## Alcance de la v1

- **Datos**: `ccxt` para descargar velas históricas diarias desde Binance (API pública,
  sin necesidad de cuenta ni API key).
- **Activos**: BTC/USDT y ETH/USDT.
- **Timeframe**: diario (1d) — menos ruido y más fácil de razonar como primer sistema.
- **Estrategia**: cruce de medias móviles (trend-following) con stop-loss porcentual y
  tamaño de posición fijo. Sirve como plantilla para probar otras ideas después.
- **Motor de backtest**: script propio en Python (pandas), sin framework externo
  (backtrader/vectorbt quedan como posible migración futura una vez validada la lógica).
- **Reporte**: gráfica de precio + señales de entrada/salida + curva de equity, y tabla
  de métricas (retorno total, win rate, máximo drawdown, Sharpe ratio).

## Por qué este enfoque (decisiones de diseño)

- Se descartó `backtrader` y `vectorbt` para la v1 porque ambos añaden una capa de
  aprendizaje (DSL de clases o pensamiento vectorizado en NumPy) antes de llegar a la
  lógica de trading en sí. Con un backtester propio, cada línea es legible y depurable.
- Se eligió timeframe diario en vez de intradía para minimizar ruido y necesidad de
  datos masivos en la primera versión.
- Migrar a `backtrader`/`vectorbt` queda como camino natural cuando se quiera: (a)
  optimizar parámetros en masa, o (b) pasar a trading en vivo/papel.

## Estado actual

Diseño aprobado (2026-08-25). Implementación completa (Tasks 1-7): datos, estrategia,
motor de backtest, métricas y reporte funcionando end-to-end. Corrida real contra la API
pública de Binance (2026-08-25), tras la ronda de fixes de la revisión final (bloqueo de
re-entrada post-stop-loss y descarte de la vela del día en formación), cruce de medias
móviles (fast=20, slow=50) con stop-loss de 5% y capital inicial de $10,000, sobre ~2
años de velas diarias:

| Símbolo  | total_return | win_rate | max_drawdown | sharpe_ratio | num_trades |
|----------|--------------|----------|---------------|--------------|------------|
| BTC/USDT | 0.4866 (48.7%) | 0.5556 (55.6%) | -0.2363 (-23.6%) | 0.8868 | 9 |
| ETH/USDT | 0.5076 (50.8%) | 0.3333 (33.3%) | -0.2483 (-24.8%) | 0.7491 | 6 |

Reportes completos (gráfica de precio+señales+equity y métricas) en `reports/`.

## Interfaz web

Además del CLI (`src/main.py`, que sigue fijo en BTC/ETH), hay una interfaz web local
(FastAPI + frontend HTML/CSS/JS a medida, sin build step) para correr el backtester
eligiendo el símbolo desde un menú de 14 pares, con gráficas interactivas (Plotly.js):
precio + medias móviles + marcadores de entrada/salida (stop-loss se ve distinto de una
salida normal), y curva de equity. Los parámetros de estrategia (20/50, stop-loss 5%,
capital $10,000) se leen del mismo `src/main.py` que usa el CLI — no están duplicados.
Ver [WEBAPP.md](WEBAPP.md) para el diseño completo.

Para correrla:

```bash
.venv/Scripts/python.exe webapp/server.py
```

Y abrir `http://127.0.0.1:8000` en el navegador.

Símbolos disponibles (`webapp/symbols.py`): BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT,
XRP/USDT, DOGE/USDT, ADA/USDT, TRX/USDT, AVAX/USDT, TON/USDT, LINK/USDT, DOT/USDT,
POL/USDT, LTC/USDT. (`MATIC/USDT` se reemplazó por `POL/USDT` porque Binance deslistó
el par MATIC.)

## Pendientes / cosas menores sin resolver

Ninguna bloqueante — el sistema funciona end-to-end y pasa sus 20 tests. Quedó
pendiente por decisión explícita (no se itera dos veces sobre el mismo hallazgo):

- **Nadie ha visto la interfaz web en un navegador real.** Este entorno no tiene
  herramientas de navegador, así que toda la verificación fue por código y `curl`. Abre
  `http://127.0.0.1:8000`, prueba un par de símbolos (incluyendo uno con pocas
  operaciones) y confirma que las gráficas se ven bien y el texto se lee con claridad.
- Ventanas de medias móviles, stop-loss y capital inicial siguen fijos — configurarlos
  desde la web es el siguiente paso natural si se quiere iterar sobre la estrategia.
- Un guard nuevo rechaza símbolos con muy pocas velas (<50), pero no se revisaron los
  otros 13 símbolos uno por uno para confirmar que todos tienen suficiente historial en
  Binance — probablemente sí, pero no se verificó exhaustivamente.
- Varios detalles cosméticos quedaron anotados en los mensajes de commit de la rama
  `sdd/webapp-v1` (ya fusionada a `master`) — nada que afecte resultados o funcionalidad.

## Próximos pasos

- [x] Escribir plan de implementación (script de datos, motor de backtest, estrategia,
      reporte)
- [x] Implementar y correr primer backtest BTC/USDT y ETH/USDT
- [x] Construir interfaz web (backend FastAPI + frontend delegado a agente de diseño UI)
- [ ] Abrir la interfaz web en un navegador real y confirmar que se ve bien
- [ ] Revisar resultados con el usuario y decidir siguientes estrategias a probar
