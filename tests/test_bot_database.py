import pytest
from bot_database import init_db, create_bot, get_bot, list_bots, update_bot_status, record_trade, get_bot_trades, get_bot_snapshots


def test_bot_database_lifecycle(tmp_path):
    db_file = tmp_path / "test_trading.db"
    init_db(db_file)

    # Crear bot
    bot = create_bot(
        bot_id="grid_sol_1",
        name="Grid SOL 10x",
        bot_type="grid",
        symbol="SOL/USDT",
        allocated_capital=100.0,
        params={"grids": 10, "lower": 95.0, "upper": 115.0},
        db_path=db_file,
    )
    assert bot["id"] == "grid_sol_1"
    assert bot["allocated_capital"] == 100.0
    assert bot["status"] == "running"
    assert bot["params"]["grids"] == 10

    # Registrar compra
    t1 = record_trade(
        bot_id="grid_sol_1",
        symbol="SOL/USDT",
        side="buy",
        price=100.0,
        qty=0.1,
        cost=10.0,
        profit=0.0,
        order_id_exchange="TEST_ORDER_1",
        db_path=db_file,
    )
    assert t1 > 0

    # Registrar venta con ganancia
    t2 = record_trade(
        bot_id="grid_sol_1",
        symbol="SOL/USDT",
        side="sell",
        price=102.0,
        qty=0.1,
        cost=10.2,
        profit=0.20,
        order_id_exchange="TEST_ORDER_2",
        db_path=db_file,
    )
    assert t2 > t1

    # Verificar acumulados del bot
    updated = get_bot("grid_sol_1", db_path=db_file)
    assert updated["total_trades"] == 2
    assert abs(updated["realized_profit"] - 0.20) < 1e-4

    # Verificar historial de trades
    trades = get_bot_trades("grid_sol_1", db_path=db_file)
    assert len(trades) == 2
    assert trades[0]["side"] == "sell"  # Orden más reciente primero

    # Verificar snapshots
    snapshots = get_bot_snapshots("grid_sol_1", db_path=db_file)
    assert len(snapshots) == 2
    assert abs(snapshots[-1]["total_equity"] - 100.20) < 1e-4

    # Pausar y listar
    update_bot_status("grid_sol_1", "stopped", db_path=db_file)
    stopped_bot = get_bot("grid_sol_1", db_path=db_file)
    assert stopped_bot["status"] == "stopped"

    active_bots = list_bots(status="running", db_path=db_file)
    assert len(active_bots) == 0

