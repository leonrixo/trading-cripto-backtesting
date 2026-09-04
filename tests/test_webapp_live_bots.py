import pytest
from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


def test_live_bots_api_lifecycle():
    # 1. Obtener balance
    res_bal = client.get("/api/live/balance")
    assert res_bal.status_code == 200
    assert "status" in res_bal.json()

    # 2. Iniciar bot
    res_start = client.post(
        "/api/live/bots",
        json={
            "bot_type": "grid",
            "symbol": "SOL/USDT",
            "allocated_capital": 50.0,
            "params": {"num_grids": 5, "interval_seconds": 1},
        },
    )
    assert res_start.status_code == 200
    data = res_start.json()
    assert data["status"] == "success"
    bot_id = data["bot"]["id"]

    # 3. Listar bots
    res_list = client.get("/api/live/bots")
    assert res_list.status_code == 200
    bots = res_list.json()["bots"]
    assert any(b["id"] == bot_id for b in bots)

    # 4. Obtener trades del bot
    res_trades = client.get(f"/api/live/bots/{bot_id}/trades")
    assert res_trades.status_code == 200
    assert "trades" in res_trades.json()

    # 5. Detener bot
    res_stop = client.post(f"/api/live/bots/{bot_id}/stop")
    assert res_stop.status_code == 200
    assert res_stop.json()["bot"]["status"] == "stopped"

    # 6. Obtener feed general de trades
    res_all_trades = client.get("/api/live/trades")
    assert res_all_trades.status_code == 200
    assert "trades" in res_all_trades.json()

