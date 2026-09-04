import pytest
from testnet_trader import check_testnet_balance, get_testnet_client


def test_testnet_trader_missing_keys():
    # Sin llaves debe retornar status 'missing_keys' con mensaje claro sin crashear
    client = get_testnet_client(api_key="", secret="")
    result = check_testnet_balance(client)
    assert result["status"] == "missing_keys"
    assert "No se encontraron llaves" in result["message"]

