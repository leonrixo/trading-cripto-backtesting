import sys
import threading
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from typing import Optional
from data import fetch_ohlcv
from strategy import generate_signals, generate_scalping_signals
from backtest import run_backtest
from grid_engine import run_grid_backtest
from metrics import compute_metrics
from main import FAST_WINDOW, SLOW_WINDOW, STOP_LOSS_PCT, INITIAL_CAPITAL
from response import build_response, _sanitize
import symbols

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI()

# Evita que dos requests concurrentes para el mismo símbolo con cache frío
# escriban el mismo CSV a la vez y lo corrompan. Suficiente para un server
# local de un solo usuario.
_fetch_lock = threading.Lock()


@app.get("/api/symbols")
def get_symbols():
    return {"symbols": symbols.SYMBOLS}


class BacktestRequest(BaseModel):
    symbol: str
    strategy_type: str = "ma"  # "ma" o "scalping_1h"
    timeframe: str = "1d"
    fast_window: Optional[int] = None
    slow_window: Optional[int] = None
    stop_loss_pct: Optional[float] = None
    initial_capital: Optional[float] = None


@app.post("/api/backtest")
def post_backtest(request: BacktestRequest):
    if request.symbol not in symbols.SYMBOLS:
        raise HTTPException(status_code=400, detail="símbolo no soportado")

    tf = "1h" if request.strategy_type == "scalping_1h" else request.timeframe
    try:
        with _fetch_lock:
            if tf == "1d":
                df = fetch_ohlcv(request.symbol)
            else:
                df = fetch_ohlcv(request.symbol, timeframe=tf)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"no se pudo descargar datos de Binance: {exc}",
        )


    if request.strategy_type == "scalping_1h":
        fast_win = request.fast_window or 9
        slow_win = request.slow_window or 21
        stop_loss = request.stop_loss_pct if request.stop_loss_pct is not None else 0.02
        capital = request.initial_capital or INITIAL_CAPITAL

        if len(df) < slow_win:
            raise HTTPException(
                status_code=400,
                detail=f"Datos insuficientes para scalping: se necesitan al menos {slow_win} velas.",
            )

        df = generate_scalping_signals(df, fast_window=fast_win, slow_window=slow_win)
        result = run_backtest(df, initial_capital=capital, stop_loss_pct=stop_loss)
        metrics = compute_metrics(result["equity_curve"], result["trades"])
        params = {
            "strategy": "scalping_1h",
            "fast_window": fast_win,
            "slow_window": slow_win,
            "stop_loss_pct": stop_loss,
            "initial_capital": capital,
            "timeframe": "1h",
        }
        return build_response(request.symbol, df, result, metrics, params)

    # Modo clásico MA (diario)
    df = generate_signals(df, FAST_WINDOW, SLOW_WINDOW)

    if len(df) < SLOW_WINDOW:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Binance solo devolvió {len(df)} velas para {request.symbol}; "
                f"se necesitan al menos {SLOW_WINDOW}."
            ),
        )

    try:
        result = run_backtest(df, initial_capital=INITIAL_CAPITAL, stop_loss_pct=STOP_LOSS_PCT)
        metrics = compute_metrics(result["equity_curve"], result["trades"])
        params = {
            "fast_window": FAST_WINDOW,
            "slow_window": SLOW_WINDOW,
            "stop_loss_pct": STOP_LOSS_PCT,
            "initial_capital": INITIAL_CAPITAL,
        }
        return build_response(request.symbol, df, result, metrics, params)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"error al procesar el backtest: {exc}")


class GridBacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "1h"
    lower_price: Optional[float] = None
    upper_price: Optional[float] = None
    num_grids: int = 10
    initial_capital: float = 10_000.0
    stop_loss_pct: Optional[float] = 0.05
    fee_pct: float = 0.001


@app.post("/api/backtest/grid")
def post_backtest_grid(request: GridBacktestRequest):
    if request.symbol not in symbols.SYMBOLS:
        raise HTTPException(status_code=400, detail="símbolo no soportado")

    try:
        with _fetch_lock:
            df = fetch_ohlcv(request.symbol, timeframe=request.timeframe)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"no se pudo descargar datos de Binance: {exc}",
        )

    if len(df) < 20:
        raise HTTPException(status_code=400, detail="datos insuficientes para la malla")

    period_min = float(df["low"].min()) if "low" in df.columns else float(df["close"].min())
    period_max = float(df["high"].max()) if "high" in df.columns else float(df["close"].max())
    lower = request.lower_price if (request.lower_price and request.lower_price > 0) else round(period_min * 0.98, 2)
    upper = request.upper_price if (request.upper_price and request.upper_price > 0) else round(period_max * 1.02, 2)
    # Si el usuario no especificó lower_price manual, no disparamos un stop-loss artificial
    stop_loss = request.stop_loss_pct if request.lower_price else None


    try:
        res = run_grid_backtest(
            df=df,
            lower_price=lower,
            upper_price=upper,
            num_grids=request.num_grids,
            initial_capital=request.initial_capital,
            fee_pct=request.fee_pct,
            stop_loss_pct=stop_loss,
        )


        dates = [d.strftime("%Y-%m-%d %H:%M") if hasattr(d, "strftime") else str(d) for d in df.index]
        close = [_sanitize(v) for v in df["close"]]
        equity = [_sanitize(v) for v in res["equity_curve"]]

        return {
            "symbol": request.symbol,
            "strategy": "grid",
            "dates": dates,
            "close": close,
            "equity_curve": equity,
            "grid_levels": res["grid_levels"],
            "grid_step": _sanitize(res["grid_step"]),
            "trades": res["trades"],
            "metrics": {
                "total_return": _sanitize(res["total_return"]),
                "realized_profit": _sanitize(res["realized_profit"]),
                "final_equity": _sanitize(res["final_equity"]),
                "num_buys": res["num_grid_buys"],
                "num_sells": res["num_grid_sells"],
                "num_trades": res["num_grid_buys"] + res["num_grid_sells"],
                "stopped_out": res["stopped_out"],
            },
            "params": {
                "lower_price": lower,
                "upper_price": upper,
                "num_grids": request.num_grids,
                "initial_capital": request.initial_capital,
                "timeframe": request.timeframe,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"error al procesar la malla: {exc}")



from bot_manager import BotManager
from testnet_trader import check_testnet_balance
from bot_database import get_bot_trades

bot_manager = BotManager()


class StartBotRequest(BaseModel):
    bot_type: str  # 'grid' o 'scalping_1h'
    symbol: str
    allocated_capital: float
    params: Optional[dict] = None


@app.get("/api/live/balance")
def get_live_balance():
    res = check_testnet_balance(bot_manager.exchange)
    return res


@app.get("/api/live/bots")
def get_live_bots():
    return {"bots": bot_manager.list_all_bots()}


@app.post("/api/live/bots")
def post_start_bot(req: StartBotRequest):
    if req.symbol not in symbols.SYMBOLS:
        raise HTTPException(status_code=400, detail="símbolo no soportado")
    try:
        bot = bot_manager.start_bot(
            bot_type=req.bot_type,
            symbol=req.symbol,
            allocated_capital=req.allocated_capital,
            params=req.params,
        )
        return {"status": "success", "bot": bot}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/live/bots/{bot_id}/stop")
def post_stop_bot(bot_id: str):
    try:
        bot = bot_manager.stop_bot(bot_id)
        return {"status": "success", "bot": bot}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/live/bots/{bot_id}/trades")
def get_trades_for_bot(bot_id: str):
    trades = get_bot_trades(bot_id, limit=50, db_path=bot_manager.db_path)
    return {"bot_id": bot_id, "trades": trades}


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
