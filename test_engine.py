import pytest
from uuid import UUID
from models import RoomStatus, TransactionType, Room, Player, Transaction
from engine import GameEngine

def test_create_room():
    engine = GameEngine()
    room = engine.create_room(room_id="123456", creator_id=111, max_players=4, initial_balance=1500)
    assert room.id == "123456"
    assert room.creator_id == 111
    assert room.max_players == 4
    assert room.initial_balance == 1500
    assert room.status == RoomStatus.PENDING

    # Duplicate room id creation should raise ValueError
    with pytest.raises(ValueError):
        engine.create_room(room_id="123456", creator_id=222, max_players=4, initial_balance=2000)

def test_join_room():
    engine = GameEngine()
    engine.create_room(room_id="room_1", creator_id=111, max_players=2, initial_balance=1500)

    # Creator joins
    p1 = engine.join_room(room_id="room_1", tg_id=111, username="creator")
    assert p1.tg_id == 111
    assert p1.username == "creator"
    assert p1.balance == 1500
    assert not p1.is_bankrupt

    # Second player joins
    p2 = engine.join_room(room_id="room_1", tg_id=222, username="player2")
    assert p2.tg_id == 222
    assert p2.balance == 1500

    # Third player joins (should exceed max_players=2)
    with pytest.raises(ValueError, match="Кімната заповнена"):
        engine.join_room(room_id="room_1", tg_id=333, username="player3")

    # Join non-existent room
    with pytest.raises(ValueError, match="Кімнату не знайдено"):
        engine.join_room(room_id="non_existent", tg_id=444, username="player4")

def test_start_game():
    engine = GameEngine()
    engine.create_room(room_id="room_1", creator_id=111, max_players=4, initial_balance=1500)
    
    # Try starting empty room
    with pytest.raises(ValueError, match="Недостатньо гравців"):
        engine.start_game("room_1")

    engine.join_room("room_1", 111, "creator")
    
    # Try starting with 1 player
    with pytest.raises(ValueError, match="Недостатньо гравців"):
        engine.start_game("room_1")

    engine.join_room("room_1", 222, "player2")
    
    # Start game
    room = engine.start_game("room_1")
    assert room.status == RoomStatus.ACTIVE

    # Try starting already started game
    with pytest.raises(ValueError, match="Гра вже розпочата"):
        engine.start_game("room_1")

    # Try joining an active game
    with pytest.raises(ValueError, match="Кімната не перебуває у режимі очікування"):
        engine.join_room("room_1", 333, "player3")

def test_execute_transaction_purchase():
    engine = GameEngine()
    engine.create_room("room_1", 111, 4, 1500)
    engine.join_room("room_1", 111, "creator")
    engine.join_room("room_1", 222, "player2")
    engine.start_game("room_1")

    # Player 1 buys from bank for 200
    tx = engine.execute_transaction(
        room_id="room_1",
        from_id=111,
        to_id="BANK",
        amount=200,
        tx_type=TransactionType.PURCHASE
    )
    assert isinstance(tx.id, UUID)
    assert tx.from_id == 111
    assert tx.to_id == "BANK"
    assert tx.amount == 200
    assert engine.players[111].balance == 1300

def test_execute_transaction_rent():
    engine = GameEngine()
    engine.create_room("room_1", 111, 4, 1500)
    engine.join_room("room_1", 111, "creator")
    engine.join_room("room_1", 222, "player2")
    engine.start_game("room_1")

    # Player 1 pays rent to Player 2
    engine.execute_transaction(
        room_id="room_1",
        from_id=111,
        to_id=222,
        amount=300,
        tx_type=TransactionType.RENT
    )
    assert engine.players[111].balance == 1200
    assert engine.players[222].balance == 1800

def test_execute_transaction_chance():
    engine = GameEngine()
    engine.create_room("room_1", 111, 4, 1500)
    engine.join_room("room_1", 111, "creator")
    engine.join_room("room_1", 222, "player2")
    engine.start_game("room_1")

    # Player 1 wins Chance (BANK pays Player 1)
    engine.execute_transaction(
        room_id="room_1",
        from_id="BANK",
        to_id=111,
        amount=150,
        tx_type=TransactionType.CHANCE_WIN
    )
    assert engine.players[111].balance == 1650

    # Player 1 loses Chance (Player 1 pays BANK)
    engine.execute_transaction(
        room_id="room_1",
        from_id=111,
        to_id="BANK",
        amount=50,
        tx_type=TransactionType.CHANCE_LOSS
    )
    assert engine.players[111].balance == 1600

def test_execute_transaction_insufficient_funds_atomicity():
    engine = GameEngine()
    engine.create_room("room_1", 111, 4, 1500)
    engine.join_room("room_1", 111, "creator")
    engine.join_room("room_1", 222, "player2")
    engine.start_game("room_1")

    # Try transaction that exceeds balance
    with pytest.raises(ValueError, match="Недостатньо коштів"):
        engine.execute_transaction(
            room_id="room_1",
            from_id=111,
            to_id=222,
            amount=1600,
            tx_type=TransactionType.RENT
        )

    # Verify balances remained unchanged
    assert engine.players[111].balance == 1500
    assert engine.players[222].balance == 1500
    assert len(engine.get_transactions("room_1")) == 0

def test_get_last_transactions():
    engine = GameEngine()
    engine.create_room("room_1", 111, 4, 1500)
    engine.join_room("room_1", 111, "creator")
    engine.join_room("room_1", 222, "player2")
    engine.start_game("room_1")

    # Execute 4 transactions
    for i in range(1, 5):
        engine.execute_transaction(
            room_id="room_1",
            from_id=111,
            to_id="BANK",
            amount=10 * i,
            tx_type=TransactionType.PURCHASE
        )

    last_txs = engine.get_last_transactions("room_1", limit=3)
    assert len(last_txs) == 3
    # Check that they are ordered by timestamp descending (most recent first)
    assert last_txs[0].amount == 40
    assert last_txs[1].amount == 30
    assert last_txs[2].amount == 20

def test_execute_transaction_validation_and_bankruptcy():
    engine = GameEngine()
    engine.create_room("room_1", 111, 4, 1500)
    engine.join_room("room_1", 111, "creator")
    engine.join_room("room_1", 222, "player2")

    # 1. Inactive game check
    with pytest.raises(ValueError, match="Гра не активна"):
        engine.execute_transaction("room_1", 111, 222, 100, TransactionType.RENT)

    engine.start_game("room_1")

    # 2. Negative/Zero amount check
    with pytest.raises(ValueError, match="Сума транзакції повинна бути більшою за 0"):
        engine.execute_transaction("room_1", 111, 222, 0, TransactionType.RENT)
    with pytest.raises(ValueError, match="Сума транзакції повинна бути більшою за 0"):
        engine.execute_transaction("room_1", 111, 222, -50, TransactionType.RENT)

    # 3. Non-existent sender/receiver check
    with pytest.raises(ValueError, match="Відправник не в цій кімнаті"):
        engine.execute_transaction("room_1", 999, 222, 100, TransactionType.RENT)
    with pytest.raises(ValueError, match="Отримувач не в цій кімнаті"):
        engine.execute_transaction("room_1", 111, 999, 100, TransactionType.RENT)

    # 4. Bankrupt checks
    engine.bankrupt_player("room_1", 222)
    assert engine.players[222].is_bankrupt
    assert engine.players[222].balance == 0

    # Bankrupt player cannot send transactions
    with pytest.raises(ValueError, match="Збанкрутілий гравець не може здійснювати операції"):
        engine.execute_transaction("room_1", 222, 111, 10, TransactionType.RENT)

    # Cannot transfer money to bankrupt player
    with pytest.raises(ValueError, match="Неможливо переказати кошти збанкрутілому гравцеві"):
        engine.execute_transaction("room_1", 111, 222, 10, TransactionType.RENT)

