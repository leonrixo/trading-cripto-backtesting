import time
import pytest
from bot_manager import BotManager


def test_bot_manager_start_and_stop(tmp_path, monkeypatch):
    db_file = tmp_path / "test_manager.db"
    manager = BotManager(db_path=db_file, max_active_bots=3)

    # Iniciar bot de malla
    bot = manager.start_bot(
        bot_type="grid",
        symbol="SOL/USDT",
        allocated_capital=50.0,
        params={"num_grids": 5, "interval_seconds": 1},
    )

    assert bot["status"] == "running"
    assert bot["symbol"] == "SOL/USDT"

    # Verificar que aparece en lista
    bots = manager.list_all_bots()
    assert len(bots) == 1
    assert bots[0]["id"] == bot["id"]

    # Detener bot
    stopped = manager.stop_bot(bot["id"])
    assert stopped["status"] == "stopped"

    # Verificar que el status refleja stopped
    status = manager.get_bot_status(bot["id"])
    assert status["is_thread_alive"] is False


def test_bot_manager_max_active_limit(tmp_path):
    db_file = tmp_path / "test_manager_limit.db"
    manager = BotManager(db_path=db_file, max_active_bots=2)

    b1 = manager.start_bot("grid", "BTC/USDT", 20.0, {"interval_seconds": 1})
    b2 = manager.start_bot("scalping_1h", "ETH/USDT", 20.0, {"interval_seconds": 1})

    # El tercero debe fallar por límite
    with pytest.raises(ValueError, match="Límite alcanzado"):
        manager.start_bot("grid", "SOL/USDT", 20.0, {"interval_seconds": 1})

    manager.stop_bot(b1["id"])
    manager.stop_bot(b2["id"])
