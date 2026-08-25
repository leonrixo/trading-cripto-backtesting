from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_get_symbols_returns_curated_list():
    response = client.get("/api/symbols")
    assert response.status_code == 200
    data = response.json()
    assert "symbols" in data
    assert "BTC/USDT" in data["symbols"]
    assert "ETH/USDT" in data["symbols"]
    assert len(data["symbols"]) == 14
