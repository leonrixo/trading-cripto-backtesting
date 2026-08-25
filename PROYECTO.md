# Trading cripto - Sistema de backtesting

**TL;DR:** Sistema en Python para probar (backtestear) estrategias de trading en cripto
sobre datos históricos, antes de arriesgar dinero real. v1: cruce de medias móviles sobre
BTC/USDT y ETH/USDT, timeframe diario. En construcción — aún no hay código.

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

Diseño aprobado (2026-08-25). Pendiente: plan de implementación y primer código.

## Próximos pasos

- [ ] Escribir plan de implementación (script de datos, motor de backtest, estrategia,
      reporte)
- [ ] Implementar y correr primer backtest BTC/USDT y ETH/USDT
- [ ] Revisar resultados con el usuario y decidir siguientes estrategias a probar
