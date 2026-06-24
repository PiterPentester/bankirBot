# Monopoly Digital Banker Bot

Telegram bot acting as a **Digital Banker** for physical Monopoly board games. The bot handles virtual rooms, player balances, and all transactions transparently. Localized in Ukrainian.

Built with Python, using the **`aiogram` v3** framework and following **Specification-Driven Development (SDD)** guidelines.

---

## 🛠️ Architecture & Features

- **Separation of Concerns**: The core engine logic (`engine.py`) is fully separated from the Telegram interface and FSM layer (`bot.py`).
- **Atomicity**: All transactions are atomic. If a transaction fails (e.g. due to insufficient funds), balances remain unchanged.
- **In-memory Persistence**: Simulates database storage using dictionaries for rooms, players, and transactions.
- **Deep-linking Lobby**: Easily create a room, set max players, configure a custom or preset starting balance, and share a generated deep link (`t.me/YOUR_BOT?start=room_CODE`) to invite players.
- **Dynamic Status Board**: The bot sends and pins a single "Global Game Status" panel for each player in their private chat, dynamically editing it in real-time as transactions are executed.
- **Full Transaction Flow**: Supports Bank purchases, rent payments to other players, Chance cards (gain/loss), and bankruptcy declaration (which stops further transfers and closes the game once 1 active player remains).

---

## 📂 Project Structure

- `models.py` — Dataclasses, schemas, and Enums representing game objects.
- `engine.py` — Pure Python core game manager handling transactions and state transitions.
- `bot.py` — The Telegram bot router, inline keyboards, FSM handlers, and localization.
- `test_engine.py` — Unit tests for the core game manager.

---

## 🚀 Setup & Execution

This project uses the modern Python packaging tool `uv`.

### 1. Installation
Clone the repository, ensure `uv` is installed, and sync dependencies:
```bash
uv sync
```

### 2. Run Tests
Run the unit test suite to verify the engine:
```bash
uv run pytest
```

### 3. Run the Telegram Bot
Obtain a bot token from `@BotFather` on Telegram, export it, and start the polling bot:
```bash
BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN" uv run python bot.py
```
