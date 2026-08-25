import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from data import fetch_ohlcv
from strategy import generate_signals
from backtest import run_backtest
from metrics import compute_metrics
from main import FAST_WINDOW, SLOW_WINDOW, STOP_LOSS_PCT, INITIAL_CAPITAL
from response import build_response
from symbols import SYMBOLS

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI()


@app.get("/api/symbols")
def get_symbols():
    return {"symbols": SYMBOLS}


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


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
