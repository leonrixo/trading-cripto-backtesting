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
