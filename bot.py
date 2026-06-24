import os
import sys
import logging
import secrets
import string
from datetime import datetime
from typing import Dict, Union

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)

from models import RoomStatus, TransactionType
from engine import GameEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize engine and routing
engine = GameEngine()
router = Router()

# Global message tracker: maps tg_id -> message_id for active game panels
panel_messages: Dict[int, int] = {}

# Global message tracker: maps tg_id -> message_id for lobby status messages
lobby_messages: Dict[int, int] = {}


# FSM States
class RoomCreation(StatesGroup):
    waiting_for_players = State()
    waiting_for_custom_players = State()
    waiting_for_balance = State()
    waiting_for_custom_balance = State()


class GamePlay(StatesGroup):
    waiting_for_buy_amount = State()
    waiting_for_rent_target = State()
    waiting_for_rent_amount = State()
    waiting_for_chance_amount = State()


# Keyboards
def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="➕ Створити кімнату")],
        [KeyboardButton(text="❓ Довідка")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(text="❌ Скасувати")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_players_count_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="2", callback_data="players_2"),
            InlineKeyboardButton(text="3", callback_data="players_3"),
            InlineKeyboardButton(text="4", callback_data="players_4")
        ],
        [
            InlineKeyboardButton(text="5", callback_data="players_5"),
            InlineKeyboardButton(text="6", callback_data="players_6")
        ],
        [
            InlineKeyboardButton(text="✏️ Власна кількість", callback_data="players_custom")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_balance_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="$1500", callback_data="balance_1500"),
            InlineKeyboardButton(text="$2000", callback_data="balance_2000"),
            InlineKeyboardButton(text="$2500", callback_data="balance_2500")
        ],
        [
            InlineKeyboardButton(text="✏️ Власна сума", callback_data="balance_custom")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_lobby_keyboard(room_id: str, is_creator: bool) -> InlineKeyboardMarkup:
    buttons = []
    if is_creator:
        buttons.append([InlineKeyboardButton(text="🚀 Розпочати гру", callback_data=f"lobby_start_{room_id}")])
    buttons.append([InlineKeyboardButton(text="🔄 Оновити", callback_data=f"lobby_refresh_{room_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_game_panel_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🛍️ Купити у Банку", callback_data="btn_buy_bank")],
        [InlineKeyboardButton(text="🏡 Сплатити ренту", callback_data="btn_pay_rent")],
        [InlineKeyboardButton(text="❓ Картка Шанс", callback_data="btn_chance")],
        [InlineKeyboardButton(text="💀 Оголосити банкрутство", callback_data="btn_bankrupt")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Helper Functions
def generate_room_code() -> str:
    # 6-character user-friendly code
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(chars) for _ in range(6))


def get_user_display_name(message_or_query: Union[Message, CallbackQuery]) -> str:
    user = message_or_query.from_user
    if user.username:
        return user.username
    return user.first_name


def format_lobby(room_id: str) -> str:
    room = engine.rooms.get(room_id)
    if not room:
        return "❌ Кімнату не знайдено."
    players = engine.get_players_in_room(room_id)
    
    text = f"🏰 <b>Лобі кімнати {room.id}</b>\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\n"
    text += f"👥 <b>Гравців приєдналося:</b> {len(players)} з {room.max_players}\n"
    text += f"💰 <b>Початковий баланс:</b> ${room.initial_balance}\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📋 <b>Список учасників:</b>\n"
    
    for idx, p in enumerate(players, 1):
        role = "👑" if p.tg_id == room.creator_id else "👤"
        text += f"{idx}. {role} @{p.username}\n"
        
    if len(players) < 2:
        text += f"\n⚠️ <i>Очікування гравців (мінімум 2 для старту)...</i>\n"
    else:
        text += f"\n✅ <i>Лобі готове до старту гри!</i>\n"
        
    return text


def format_game_status(room_id: str) -> str:
    room = engine.rooms.get(room_id)
    if not room:
        return "❌ Кімнату не знайдено."
    
    players = engine.get_players_in_room(room_id)
    
    text = f"🎲 <b>Монополія — Кімната {room.id}</b> 🎲\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 <b>Рахунки гравців:</b>\n"
    
    for idx, player in enumerate(players, 1):
        status_icon = "👤"
        status_suffix = ""
        if player.is_bankrupt:
            status_icon = "💀"
            status_suffix = " <i>(Банкрут)</i>"
        elif player.tg_id == room.creator_id:
            status_icon = "👑"
            
        text += f"{idx}. {status_icon} <b>@{player.username}</b>: ${player.balance}{status_suffix}\n"
        
    text += f"━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📜 <b>Останні 3 транзакції:</b>\n"
    
    last_txs = engine.get_last_transactions(room_id, limit=3)
    if not last_txs:
        text += "<i>Транзакцій ще не було</i>\n"
    else:
        for tx in last_txs:
            # Format source
            if tx.from_id == "BANK":
                from_str = "🏦 Банк"
            else:
                sender_player = engine.players.get(tx.from_id)
                from_str = f"@{sender_player.username}" if sender_player else "Невідомий"
                
            # Format destination
            if tx.to_id == "BANK":
                to_str = "🏦 Банк"
            else:
                receiver_player = engine.players.get(tx.to_id)
                to_str = f"@{receiver_player.username}" if receiver_player else "Невідомий"
                
            # Translate transaction type
            tx_type_str = ""
            if tx.type == TransactionType.PURCHASE:
                tx_type_str = "Купівля"
            elif tx.type == TransactionType.RENT:
                tx_type_str = "Оренда"
            elif tx.type == TransactionType.CHANCE_WIN:
                tx_type_str = "Шанс (Виграш)"
            elif tx.type == TransactionType.CHANCE_LOSS:
                tx_type_str = "Шанс (Штраф)"
                
            text += f"• {from_str} ➡️ {to_str}: <b>${tx.amount}</b> ({tx_type_str})\n"
            
    text += f"━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🕒 Оновлено: <code>{datetime.now().strftime('%H:%M:%S')}</code>"
    return text


async def update_lobby_messages(room_id: str, bot: Bot):
    players = engine.get_players_in_room(room_id)
    room = engine.rooms.get(room_id)
    if not room:
        return
        
    lobby_text = format_lobby(room_id)
    for p in players:
        msg_id = lobby_messages.get(p.tg_id)
        if msg_id:
            try:
                is_creator = (p.tg_id == room.creator_id)
                await bot.edit_message_text(
                    chat_id=p.tg_id,
                    message_id=msg_id,
                    text=lobby_text,
                    reply_markup=get_lobby_keyboard(room_id, is_creator)
                )
            except Exception as e:
                if "message is not modified" in str(e):
                    logger.debug(f"Lobby message for player {p.tg_id} not modified.")
                else:
                    logger.error(f"Failed to edit lobby message for player {p.tg_id}: {e}")


async def update_room_panels(room_id: str, bot: Bot):
    players = engine.get_players_in_room(room_id)
    status_text = format_game_status(room_id)
    panel_kb = get_game_panel_keyboard()
    
    for p in players:
        msg_id = panel_messages.get(p.tg_id)
        if msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=p.tg_id,
                    message_id=msg_id,
                    text=status_text,
                    reply_markup=panel_kb
                )
            except Exception as e:
                if "message is not modified" in str(e):
                    logger.debug(f"Status panel for player {p.tg_id} not modified.")
                else:
                    logger.warning(f"Failed to edit panel for player {p.tg_id}, sending new one: {e}")
                    # If editing failed, try sending a new panel
                    try:
                        new_msg = await bot.send_message(
                            chat_id=p.tg_id,
                            text=status_text,
                            reply_markup=panel_kb
                        )
                        panel_messages[p.tg_id] = new_msg.message_id
                        try:
                            await bot.pin_chat_message(chat_id=p.tg_id, message_id=new_msg.message_id)
                        except Exception:
                            pass
                    except Exception as send_err:
                        logger.error(f"Failed to send new panel to {p.tg_id}: {send_err}")


async def broadcast_to_room(room_id: str, bot: Bot, text: str):
    players = engine.get_players_in_room(room_id)
    for p in players:
        try:
            await bot.send_message(chat_id=p.tg_id, text=text)
        except Exception as e:
            logger.error(f"Failed to broadcast to player {p.tg_id}: {e}")


# Command Handlers
@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    
    args = command.args
    tg_id = message.from_user.id
    username = get_user_display_name(message)
    
    if args and args.startswith("room_"):
        room_id = args.split("room_")[1]
        try:
            player = engine.join_room(room_id, tg_id, username)
            await message.answer(
                f"✅ Ви успішно приєдналися до кімнати <b>{room_id}</b>!",
                reply_markup=get_main_keyboard()
            )
            
            # Send/Update lobby status
            lobby_text = format_lobby(room_id)
            room = engine.rooms[room_id]
            is_creator = (tg_id == room.creator_id)
            
            msg = await message.answer(
                lobby_text,
                reply_markup=get_lobby_keyboard(room_id, is_creator)
            )
            lobby_messages[tg_id] = msg.message_id
            
            # Notify other players and refresh their lobby UI
            await broadcast_to_room(room_id, message.bot, f"👤 Гравець @{username} приєднався до кімнати!")
            await update_lobby_messages(room_id, message.bot)
            
        except ValueError as e:
            await message.answer(f"❌ Помилка: {str(e)}", reply_markup=get_main_keyboard())
        return

    # Standard /start invitation
    welcome_text = (
        "👋 Вітаємо у <b>Digital Banker Monopoly</b>!\n\n"
        "Цей бот допоможе вам вести рахунки та транзакції під час гри в настільну Монополію.\n\n"
        "Оберіть дію нижче:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard())


@router.message(Command("cancel"))
@router.message(F.text.casefold() == "скасувати")
@router.message(F.text == "❌ Скасувати")
async def cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Немає активних операцій для скасування.", reply_markup=get_main_keyboard())
        return

    await state.clear()
    await message.answer("❌ Операцію скасовано.", reply_markup=get_main_keyboard())


@router.message(Command("help"))
@router.message(F.text == "❓ Довідка")
async def cmd_help(message: Message):
    help_text = (
        "📚 <b>Як грати з Digital Banker:</b>\n\n"
        "1️⃣ Один гравець натискає <b>➕ Створити кімнату</b>, обирає ліміт гравців та початковий баланс.\n"
        "2️⃣ Бот генерує унікальне посилання для приєднання.\n"
        "3️⃣ Інші гравці переходять за посиланням і автоматично потрапляють до лобі.\n"
        "4️⃣ Творець кімнати натискає <b>🚀 Розпочати гру</b>.\n"
        "5️⃣ Кожен гравець отримує закріплену панель для проведення операцій: покупка у Банку, оплата ренти іншому гравцеві чи картки Шанс.\n\n"
        "💡 <i>Всі транзакції відбуваються миттєво та автоматично оновлюють рахунки всіх учасників.</i>"
    )
    await message.answer(help_text, reply_markup=get_main_keyboard())


# Room Creation Flow
@router.message(F.text == "➕ Створити кімнату")
async def process_create_room(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(RoomCreation.waiting_for_players)
    await message.answer(
        "👥 Оберіть кількість гравців для вашої кімнати (від 2 до 6):",
        reply_markup=get_players_count_keyboard()
    )


@router.callback_query(RoomCreation.waiting_for_players, F.data.startswith("players_"))
async def process_players_callback(callback: CallbackQuery, state: FSMContext):
    selection = callback.data.split("_")[1]
    await callback.answer()
    
    if selection == "custom":
        await state.set_state(RoomCreation.waiting_for_custom_players)
        await callback.message.edit_text(
            "✏️ Введіть бажану кількість гравців (ціле число від 2 до 12):"
        )
    else:
        max_players = int(selection)
        await state.update_data(max_players=max_players)
        await state.set_state(RoomCreation.waiting_for_balance)
        await callback.message.edit_text(
            "💰 Оберіть початковий баланс для кожного гравця:",
            reply_markup=get_balance_keyboard()
        )


@router.message(RoomCreation.waiting_for_custom_players)
async def process_custom_players(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("❌ Будь ласка, введіть ціле число:")
        return
        
    players_count = int(text)
    if players_count < 2 or players_count > 12:
        await message.answer("❌ Кількість гравців має бути від 2 до 12. Спробуйте ще раз:")
        return
        
    await state.update_data(max_players=players_count)
    await state.set_state(RoomCreation.waiting_for_balance)
    await message.answer(
        "💰 Оберіть початковий баланс для кожного гравця:",
        reply_markup=get_balance_keyboard()
    )


@router.callback_query(RoomCreation.waiting_for_balance, F.data.startswith("balance_"))
async def process_balance_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    selection = callback.data.split("_")[1]
    
    if selection == "custom":
        await state.set_state(RoomCreation.waiting_for_custom_balance)
        await callback.message.edit_text("✏️ Введіть початковий баланс (ціле число від 100 до 100000):")
    else:
        balance = int(selection)
        await finalize_room_creation(callback.message, state, balance)


@router.message(RoomCreation.waiting_for_custom_balance)
async def process_custom_balance(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("❌ Будь ласка, введіть ціле число:")
        return
        
    balance = int(text)
    if balance < 100 or balance > 100000:
        await message.answer("❌ Сума має бути в межах від 100 до 100000. Спробуйте ще раз:")
        return
        
    await finalize_room_creation(message, state, balance)


async def finalize_room_creation(message: Message, state: FSMContext, initial_balance: int):
    data = await state.get_data()
    max_players = data.get("max_players")
    
    room_id = generate_room_code()
    tg_id = message.chat.id
    username = get_user_display_name(message)
    
    try:
        # Create and join
        engine.create_room(room_id, tg_id, max_players, initial_balance)
        engine.join_room(room_id, tg_id, username)
        
        bot_info = await message.bot.get_me()
        deep_link = f"https://t.me/{bot_info.username}?start=room_{room_id}"
        
        setup_text = (
            f"✅ <b>Кімнату {room_id} успішно створено!</b>\n\n"
            f"🔗 Надішліть це посилання іншим гравцям для приєднання:\n"
            f"<code>{deep_link}</code>\n\n"
            f"<i>Після приєднання всіх гравців натисніть кнопку 'Розпочати гру' в лобі нижче.</i>"
        )
        
        await message.answer(setup_text, reply_markup=get_main_keyboard())
        
        # Display lobby
        lobby_text = format_lobby(room_id)
        lobby_msg = await message.answer(
            lobby_text,
            reply_markup=get_lobby_keyboard(room_id, is_creator=True)
        )
        lobby_messages[tg_id] = lobby_msg.message_id
        
        await state.clear()
        
    except ValueError as e:
        await message.answer(f"❌ Помилка при створенні кімнати: {str(e)}", reply_markup=get_main_keyboard())
        await state.clear()


# Lobby Callbacks (Start Game & Refresh)
@router.callback_query(F.data.startswith("lobby_start_"))
async def process_lobby_start(callback: CallbackQuery):
    room_id = callback.data.split("lobby_start_")[1]
    tg_id = callback.from_user.id
    
    room = engine.rooms.get(room_id)
    if not room:
        await callback.answer("❌ Кімнату не знайдено.", show_alert=True)
        return
        
    if room.creator_id != tg_id:
        await callback.answer("❌ Тільки творець кімнати може розпочати гру.", show_alert=True)
        return
        
    try:
        engine.start_game(room_id)
        await callback.answer("🎮 Гра починається!")
        
        # Clear lobby message entries
        players = engine.get_players_in_room(room_id)
        for p in players:
            msg_id = lobby_messages.pop(p.tg_id, None)
            if msg_id:
                try:
                    await callback.bot.delete_message(chat_id=p.tg_id, message_id=msg_id)
                except Exception:
                    pass
                    
        # Send new Global Status Panel to everyone and pin it
        status_text = format_game_status(room_id)
        panel_kb = get_game_panel_keyboard()
        
        for p in players:
            msg = await callback.bot.send_message(
                chat_id=p.tg_id,
                text=status_text,
                reply_markup=panel_kb
            )
            panel_messages[p.tg_id] = msg.message_id
            try:
                await callback.bot.pin_chat_message(chat_id=p.tg_id, message_id=msg.message_id)
            except Exception:
                pass
                
        await broadcast_to_room(room_id, callback.bot, "🚀 <b>Гра розпочалася! Панель керування банком надіслана кожному учаснику.</b>")
        
    except ValueError as e:
        await callback.answer(f"❌ Помилка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("lobby_refresh_"))
async def process_lobby_refresh(callback: CallbackQuery):
    room_id = callback.data.split("lobby_refresh_")[1]
    room = engine.rooms.get(room_id)
    if not room:
        await callback.answer("❌ Кімнату не знайдено.", show_alert=True)
        return
        
    await callback.answer("🔄 Оновлено")
    await update_lobby_messages(room_id, callback.bot)


# Gameplay Actions (Buy, Rent, Chance, Bankrupt)
@router.callback_query(F.data == "btn_buy_bank")
async def process_btn_buy(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    player = engine.players.get(tg_id)
    
    if not player:
        await callback.answer("❌ Ви не берете участі у грі.", show_alert=True)
        return
        
    if player.is_bankrupt:
        await callback.answer("❌ Збанкрутілі гравці не можуть здійснювати операції.", show_alert=True)
        return
        
    room = engine.rooms.get(player.room_id)
    if not room or room.status != RoomStatus.ACTIVE:
        await callback.answer("❌ Гра не активна.", show_alert=True)
        return
        
    await callback.answer()
    await state.set_state(GamePlay.waiting_for_buy_amount)
    await state.update_data(room_id=player.room_id)
    
    await callback.message.answer(
        "🛍️ <b>Купівля у Банку:</b>\n"
        "Введіть суму покупки (ціле число):",
        reply_markup=get_cancel_keyboard()
    )


@router.message(GamePlay.waiting_for_buy_amount)
async def process_buy_amount(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("❌ Будь ласка, введіть додатне ціле число:")
        return
        
    amount = int(text)
    data = await state.get_data()
    room_id = data.get("room_id")
    tg_id = message.from_user.id
    username = get_user_display_name(message)
    
    try:
        engine.execute_transaction(
            room_id=room_id,
            from_id=tg_id,
            to_id="BANK",
            amount=amount,
            tx_type=TransactionType.PURCHASE
        )
        
        await message.answer(
            f"✅ Успішно! Ви сплатили Банку ${amount}.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        
        # Broadcast and update UI
        await broadcast_to_room(room_id, message.bot, f"💸 @{username} сплатив Банку <b>${amount}</b> за покупку.")
        await update_room_panels(room_id, message.bot)
        
    except ValueError as e:
        await message.answer(f"❌ Insufficient funds! ({str(e)})", reply_markup=get_main_keyboard())
        await state.clear()


@router.callback_query(F.data == "btn_pay_rent")
async def process_btn_rent(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    player = engine.players.get(tg_id)
    
    if not player:
        await callback.answer("❌ Ви не берете участі у грі.", show_alert=True)
        return
        
    if player.is_bankrupt:
        await callback.answer("❌ Збанкрутілі гравці не можуть здійснювати операції.", show_alert=True)
        return
        
    room = engine.rooms.get(player.room_id)
    if not room or room.status != RoomStatus.ACTIVE:
        await callback.answer("❌ Гра не активна.", show_alert=True)
        return
        
    # Get other active players in room
    other_players = [p for p in engine.get_players_in_room(player.room_id) if p.tg_id != tg_id and not p.is_bankrupt]
    
    if not other_players:
        await callback.answer("❌ Немає інших активних гравців для сплати оренди.", show_alert=True)
        return
        
    await callback.answer()
    
    # Create selection keyboard
    buttons = []
    for op in other_players:
        buttons.append([InlineKeyboardButton(text=f"👤 @{op.username}", callback_data=f"rent_target_{op.tg_id}")])
    buttons.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="rent_cancel")])
    
    await state.set_state(GamePlay.waiting_for_rent_target)
    await state.update_data(room_id=player.room_id)
    await callback.message.answer(
        "🏡 <b>Сплата ренти:</b>\n"
        "Оберіть гравця, якому хочете сплатити:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(GamePlay.waiting_for_rent_target, F.data == "rent_cancel")
async def process_rent_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ Операцію скасовано.")


@router.callback_query(GamePlay.waiting_for_rent_target, F.data.startswith("rent_target_"))
async def process_rent_target(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split("_")[2])
    target_player = engine.players.get(target_id)
    
    if not target_player:
        await callback.answer("❌ Гравця не знайдено.", show_alert=True)
        await state.clear()
        return
        
    await callback.answer()
    await state.update_data(rent_target_id=target_id)
    await state.set_state(GamePlay.waiting_for_rent_amount)
    
    await callback.message.edit_text(
        f"🏡 <b>Сплата ренти для @{target_player.username}:</b>\n"
        f"Введіть суму оренди (ціле число):",
        reply_markup=None
    )
    # We send a message with cancel keyboard so they have the button
    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text="Ви можете скасувати операцію, натиснувши на кнопку нижче або відправивши /cancel.",
        reply_markup=get_cancel_keyboard()
    )


@router.message(GamePlay.waiting_for_rent_amount)
async def process_rent_amount(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("❌ Будь ласка, введіть додатне ціле число:")
        return
        
    amount = int(text)
    data = await state.get_data()
    room_id = data.get("room_id")
    target_id = data.get("rent_target_id")
    tg_id = message.from_user.id
    
    sender_username = get_user_display_name(message)
    target_player = engine.players.get(target_id)
    target_username = target_player.username if target_player else "Невідомий"
    
    try:
        engine.execute_transaction(
            room_id=room_id,
            from_id=tg_id,
            to_id=target_id,
            amount=amount,
            tx_type=TransactionType.RENT
        )
        
        await message.answer(
            f"✅ Успішно! Ви перевели ${amount} для @{target_username}.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        
        # Broadcast and update UI
        await broadcast_to_room(room_id, message.bot, f"💸 @{sender_username} сплатив оренду @{target_username} на суму <b>${amount}</b>.")
        await update_room_panels(room_id, message.bot)
        
    except ValueError as e:
        await message.answer(f"❌ Insufficient funds! ({str(e)})", reply_markup=get_main_keyboard())
        await state.clear()


# Chance Handler
@router.callback_query(F.data == "btn_chance")
async def process_btn_chance(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    player = engine.players.get(tg_id)
    
    if not player:
        await callback.answer("❌ Ви не берете участі у грі.", show_alert=True)
        return
        
    if player.is_bankrupt:
        await callback.answer("❌ Збанкрутілі гравці не можуть здійснювати операції.", show_alert=True)
        return
        
    room = engine.rooms.get(player.room_id)
    if not room or room.status != RoomStatus.ACTIVE:
        await callback.answer("❌ Гра не активна.", show_alert=True)
        return
        
    await callback.answer()
    
    buttons = [
        [
            InlineKeyboardButton(text="➕ Отримати гроші", callback_data="chance_action_gain"),
            InlineKeyboardButton(text="➖ Втратити гроші", callback_data="chance_action_lose")
        ],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="chance_cancel")]
    ]
    
    await state.update_data(room_id=player.room_id)
    await callback.message.answer(
        "❓ <b>Картка Шанс:</b>\n"
        "Оберіть тип операції з Банком:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data == "chance_cancel")
async def process_chance_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ Операцію скасовано.")


@router.callback_query(F.data.startswith("chance_action_"))
async def process_chance_action(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[2]  # gain or lose
    await callback.answer()
    
    await state.update_data(chance_type=action)
    await state.set_state(GamePlay.waiting_for_chance_amount)
    
    action_text = "отримати від Банку" if action == "gain" else "сплатити Банку"
    
    await callback.message.edit_text(
        f"❓ <b>Картка Шанс ({action_text}):</b>\n"
        f"Введіть суму (ціле число):",
        reply_markup=None
    )
    
    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text="Ви можете скасувати операцію, натиснувши на кнопку нижче або відправивши /cancel.",
        reply_markup=get_cancel_keyboard()
    )


@router.message(GamePlay.waiting_for_chance_amount)
async def process_chance_amount(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("❌ Будь ласка, введіть додатне ціле число:")
        return
        
    amount = int(text)
    data = await state.get_data()
    room_id = data.get("room_id")
    chance_type = data.get("chance_type")
    tg_id = message.from_user.id
    username = get_user_display_name(message)
    
    try:
        if chance_type == "gain":
            engine.execute_transaction(
                room_id=room_id,
                from_id="BANK",
                to_id=tg_id,
                amount=amount,
                tx_type=TransactionType.CHANCE_WIN
            )
            await message.answer(
                f"✅ Успішно! Ви отримали від Банку ${amount}.",
                reply_markup=get_main_keyboard()
            )
            await broadcast_to_room(room_id, message.bot, f"🎁 @{username} отримав від Банку <b>${amount}</b> за карткою Шанс.")
        else:
            engine.execute_transaction(
                room_id=room_id,
                from_id=tg_id,
                to_id="BANK",
                amount=amount,
                tx_type=TransactionType.CHANCE_LOSS
            )
            await message.answer(
                f"✅ Успішно! Ви сплатили Банку ${amount}.",
                reply_markup=get_main_keyboard()
            )
            await broadcast_to_room(room_id, message.bot, f"💸 @{username} сплатив Банку <b>${amount}</b> за карткою Шанс.")
            
        await state.clear()
        await update_room_panels(room_id, message.bot)
        
    except ValueError as e:
        await message.answer(f"❌ Insufficient funds! ({str(e)})", reply_markup=get_main_keyboard())
        await state.clear()


# Bankruptcy Handler
@router.callback_query(F.data == "btn_bankrupt")
async def process_btn_bankrupt(callback: CallbackQuery):
    tg_id = callback.from_user.id
    player = engine.players.get(tg_id)
    
    if not player:
        await callback.answer("❌ Ви не берете участі у грі.", show_alert=True)
        return
        
    if player.is_bankrupt:
        await callback.answer("❌ Ви вже є банкрутом.", show_alert=True)
        return
        
    room = engine.rooms.get(player.room_id)
    if not room or room.status != RoomStatus.ACTIVE:
        await callback.answer("❌ Гра не активна.", show_alert=True)
        return
        
    await callback.answer()
    
    buttons = [
        [
            InlineKeyboardButton(text="💀 Так, я банкрут", callback_data="bankrupt_confirm"),
            InlineKeyboardButton(text="❌ Ні, скасувати", callback_data="bankrupt_cancel")
        ]
    ]
    await callback.message.answer(
        "⚠️ <b>Оголошення банкрутства:</b>\n"
        "Ви впевнені, що хочете оголосити банкрутство? Ваш рахунок буде анульовано, і ви більше не зможете брати участь у транзакціях.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data == "bankrupt_cancel")
async def process_bankrupt_cancel(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("❌ Операцію скасовано.")


@router.callback_query(F.data == "bankrupt_confirm")
async def process_bankrupt_confirm(callback: CallbackQuery):
    tg_id = callback.from_user.id
    player = engine.players.get(tg_id)
    
    if not player or player.is_bankrupt:
        await callback.answer("❌ Ви не можете виконати цю операцію.", show_alert=True)
        return
        
    room_id = player.room_id
    await callback.answer()
    await callback.message.edit_text("💀 Ви оголосили себе банкрутом.")
    
    engine.bankrupt_player(room_id, tg_id)
    
    # Broadcast to room
    await broadcast_to_room(room_id, callback.bot, f"💀 Гравець @{player.username} оголосив себе банкрутом!")
    
    # Check if only 1 active player remains
    active_players = [p for p in engine.get_players_in_room(room_id) if not p.is_bankrupt]
    if len(active_players) <= 1:
        # Game finished
        room = engine.rooms[room_id]
        room.status = RoomStatus.FINISHED
        
        winner_name = f"@{active_players[0].username}" if active_players else "Ніхто"
        await broadcast_to_room(
            room_id,
            callback.bot,
            f"🏆 <b>Гру завершено!</b>\nПереможець гри: {winner_name} 🎉"
        )
        
        # Edit everyone's game panel to show finished status and remove markup
        finished_text = format_game_status(room_id) + "\n\n🏁 <b>Гру завершено! Панель неактивна.</b>"
        players = engine.get_players_in_room(room_id)
        for p in players:
            msg_id = panel_messages.get(p.tg_id)
            if msg_id:
                try:
                    await callback.bot.edit_message_text(
                        chat_id=p.tg_id,
                        message_id=msg_id,
                        text=finished_text,
                        reply_markup=None
                    )
                except Exception:
                    pass
    else:
        # Update panels for everyone remaining
        await update_room_panels(room_id, callback.bot)


# Main Entry point
async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ Помилка: Змінна середовища BOT_TOKEN не знайдена.", file=sys.stderr)
        print("Будь ласка, запустіть бот командою: BOT_TOKEN='your_token' python bot.py", file=sys.stderr)
        sys.exit(1)

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    print("🤖 Бот запускається...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
