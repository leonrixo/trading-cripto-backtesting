# Trading cripto - Sistema de backtesting

**TL;DR:** Sistema en Python para probar (backtestear) estrategias de trading en cripto
sobre datos históricos, antes de arriesgar dinero real. v1: cruce de medias móviles sobre
BTC/USDT y ETH/USDT, timeframe diario. Sistema implementado y corrido contra datos reales
de Binance (ver Estado actual más abajo).

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

## Próximos pasos

- [x] Escribir plan de implementación (script de datos, motor de backtest, estrategia,
      reporte)
- [x] Implementar y correr primer backtest BTC/USDT y ETH/USDT
- [ ] Revisar resultados con el usuario y decidir siguientes estrategias a probar
