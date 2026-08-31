# Crypto Backtesting Engine

A moving-average crossover strategy backtester for crypto pairs, built to get the methodology right before ever risking real capital: no look-ahead bias, realistic stop-loss handling, and metrics computed the way a quant would check them, not approximated.

## Methodology

- **Strategy:** fast/slow moving average crossover (20/50 period, daily candles) on `BTC/USDT` and `ETH/USDT`.
- **No look-ahead bias:** signals are shifted by one period (`shift(1)`) before being applied, so a trade can only act on information that was actually available at that point in time.
- **Stop-loss evaluated against the close**, not the intraday low, with the assumption documented in code — and re-entry after a stop-loss is blocked to avoid re-triggering on the same move.
- Positions are force-closed at the end of the available data so no trade is left open when metrics are computed.

## Metrics

Computed from the equity curve and trade log, not just eyeballed:

- **Sharpe ratio** (annualized)
- **Max drawdown** (via running `cummax()`)
- **Win rate** and **total return**

## Architecture

```
data.py      -> fetch OHLCV candles from Binance's public API via ccxt (no account/API key needed)
strategy.py  -> generate MA crossover signals (look-ahead safe)
backtest.py  -> simulate trades against the signals, apply stop-loss
metrics.py   -> Sharpe, drawdown, win rate, total return
report.py    -> price/signals/equity-curve PNG reports
webapp/      -> FastAPI + Plotly web UI for interactive runs
```

Market data is cached locally as CSV so repeated runs don't re-hit the API.

## Stack

Python, pandas, numpy, ccxt, FastAPI, Plotly.js, pytest.

## How to run

```bash
pip install -r requirements.txt

# CLI: runs the backtest for BTC/USDT and ETH/USDT, writes reports/
python src/main.py

# Web UI: interactive backtests with charts
python webapp/server.py
```

## Tests

20 tests with pytest, covering the backtest engine, data layer, metrics, report generation, strategy signals and the web API endpoints:

```bash
pytest
```

## Limitations

This is a single backtest run over one historical window, not a walk-forward or out-of-sample validation, and it doesn't model trading fees or slippage. The point of this project is the methodology (avoiding look-ahead bias, computing metrics correctly, testing the engine itself) rather than the specific return numbers a given run produces.
