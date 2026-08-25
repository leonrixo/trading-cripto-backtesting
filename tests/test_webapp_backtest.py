from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_backtest_rejects_unsupported_symbol():
    response = client.post("/api/backtest", json={"symbol": "FAKE/USDT"})
    assert response.status_code == 400
