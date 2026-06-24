from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID
from typing import Union

class RoomStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    FINISHED = "FINISHED"

class TransactionType(str, Enum):
    PURCHASE = "PURCHASE"
    RENT = "RENT"
    CHANCE_WIN = "CHANCE_WIN"
    CHANCE_LOSS = "CHANCE_LOSS"

@dataclass
class Room:
    id: str  # unique room code
    creator_id: int
    max_players: int
    initial_balance: int
    status: RoomStatus

@dataclass
class Player:
    tg_id: int
    username: str
    room_id: str
    balance: int
    is_bankrupt: bool = False

@dataclass
class Transaction:
    id: UUID
    room_id: str
    from_id: Union[int, str]  # tg_id of sender or 'BANK'
    to_id: Union[int, str]    # tg_id of receiver or 'BANK'
    amount: int
    type: TransactionType
    timestamp: datetime
