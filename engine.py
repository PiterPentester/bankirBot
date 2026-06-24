import uuid
from datetime import datetime
from typing import Union, Dict, List
from models import Room, Player, Transaction, RoomStatus, TransactionType

class GameEngine:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        # Players are keyed by their Telegram ID
        self.players: Dict[int, Player] = {}
        # Transactions are keyed by their UUID
        self.transactions: Dict[uuid.UUID, Transaction] = {}

    def create_room(self, room_id: str, creator_id: int, max_players: int, initial_balance: int) -> Room:
        if room_id in self.rooms:
            raise ValueError("Кімната з таким ID вже існує")
        
        room = Room(
            id=room_id,
            creator_id=creator_id,
            max_players=max_players,
            initial_balance=initial_balance,
            status=RoomStatus.PENDING
        )
        self.rooms[room_id] = room
        return room

    def join_room(self, room_id: str, tg_id: int, username: str) -> Player:
        if room_id not in self.rooms:
            raise ValueError("Кімнату не знайдено")
        
        room = self.rooms[room_id]
        if room.status != RoomStatus.PENDING:
            raise ValueError("Кімната не перебуває у режимі очікування")
        
        # Check if already joined this room
        if tg_id in self.players:
            player = self.players[tg_id]
            if player.room_id == room_id:
                # If they are already in the room, just return them
                return player
            else:
                # Move player to new room (or raise error, let's allow moving to new room for simplicity)
                # Remove from old room counting logic if necessary
                player.room_id = room_id
                player.balance = room.initial_balance
                player.is_bankrupt = False
                return player

        # Check max players limit
        current_players = self.get_players_in_room(room_id)
        if len(current_players) >= room.max_players:
            raise ValueError("Кімната заповнена")

        player = Player(
            tg_id=tg_id,
            username=username,
            room_id=room_id,
            balance=room.initial_balance,
            is_bankrupt=False
        )
        self.players[tg_id] = player
        return player

    def get_players_in_room(self, room_id: str) -> List[Player]:
        return [p for p in self.players.values() if p.room_id == room_id]

    def start_game(self, room_id: str) -> Room:
        if room_id not in self.rooms:
            raise ValueError("Кімнату не знайдено")
        
        room = self.rooms[room_id]
        if room.status == RoomStatus.ACTIVE:
            raise ValueError("Гра вже розпочата")
        elif room.status == RoomStatus.FINISHED:
            raise ValueError("Гра вже завершена")
        
        players = self.get_players_in_room(room_id)
        if len(players) < 2:
            raise ValueError("Недостатньо гравців (мінімум 2)")
        
        room.status = RoomStatus.ACTIVE
        return room

    def execute_transaction(
        self,
        room_id: str,
        from_id: Union[int, str],
        to_id: Union[int, str],
        amount: int,
        tx_type: TransactionType
    ) -> Transaction:
        if room_id not in self.rooms:
            raise ValueError("Кімнату не знайдено")
        
        room = self.rooms[room_id]
        if room.status != RoomStatus.ACTIVE:
            raise ValueError("Гра не активна")

        if amount <= 0:
            raise ValueError("Сума транзакції повинна бути більшою за 0")

        # Validate sender if it is a player
        sender = None
        if from_id != "BANK":
            if not isinstance(from_id, int):
                raise ValueError("Некоректний ID відправника")
            sender = self.players.get(from_id)
            if not sender or sender.room_id != room_id:
                raise ValueError("Відправник не в цій кімнаті")
            if sender.is_bankrupt:
                raise ValueError("Збанкрутілий гравець не може здійснювати операції")
            if sender.balance < amount:
                raise ValueError("Недостатньо коштів!")

        # Validate receiver if it is a player
        receiver = None
        if to_id != "BANK":
            if not isinstance(to_id, int):
                raise ValueError("Некоректний ID отримувача")
            receiver = self.players.get(to_id)
            if not receiver or receiver.room_id != room_id:
                raise ValueError("Отримувач не в цій кімнаті")
            if receiver.is_bankrupt:
                raise ValueError("Неможливо переказати кошти збанкрутілому гравцеві")

        # Perform atomic transaction
        if sender:
            sender.balance -= amount
        if receiver:
            receiver.balance += amount

        # Create and save transaction record
        tx = Transaction(
            id=uuid.uuid4(),
            room_id=room_id,
            from_id=from_id,
            to_id=to_id,
            amount=amount,
            type=tx_type,
            timestamp=datetime.now()
        )
        self.transactions[tx.id] = tx
        return tx

    def get_transactions(self, room_id: str) -> List[Transaction]:
        return [tx for tx in self.transactions.values() if tx.room_id == room_id]

    def get_last_transactions(self, room_id: str, limit: int = 3) -> List[Transaction]:
        txs = self.get_transactions(room_id)
        # Sort by timestamp descending (newest first)
        txs.sort(key=lambda x: x.timestamp, reverse=True)
        return txs[:limit]
        
    def bankrupt_player(self, room_id: str, tg_id: int) -> Player:
        if tg_id not in self.players:
            raise ValueError("Гравця не знайдено")
        player = self.players[tg_id]
        if player.room_id != room_id:
            raise ValueError("Гравець не в цій кімнаті")
        player.is_bankrupt = True
        player.balance = 0
        return player
