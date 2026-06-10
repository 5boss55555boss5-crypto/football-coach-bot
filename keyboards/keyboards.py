import os
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

TACTICS_LIST = [
    ("🔥 Атакувальна", "tactic_attack"),
    ("🧱 Захисна", "tactic_defense"),
    ("⚖️ Збалансована", "tactic_balanced"),
    ("⚡️ Контратаки", "tactic_counter"),
    ("🎯 Високий пресинг", "tactic_pressing"),
    ("🧠 Контроль м'яча", "tactic_possession"),
]

TACTICS_NAMES = {
    "tactic_attack": "🔥 Атакувальна",
    "tactic_defense": "🧱 Захисна",
    "tactic_balanced": "⚖️ Збалансована",
    "tactic_counter": "⚡️ Контратаки",
    "tactic_pressing": "🎯 Високий пресинг",
    "tactic_possession": "🧠 Контроль м'яча",
}

TACTICS_BONUS = {
    "tactic_attack": 5,
    "tactic_defense": 2,
    "tactic_balanced": 3,
    "tactic_counter": 4,
    "tactic_pressing": 4,
    "tactic_possession": 3,
}


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    web_url = os.getenv("WEB_URL", "").strip()
    if web_url and web_url.startswith("https://"):
        builder.row(
            InlineKeyboardButton(text="🎮 Грати гру", web_app=WebAppInfo(url=web_url))
        )
    return builder.as_markup()


def clubs_keyboard(clubs: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for club in clubs:
        builder.row(
            InlineKeyboardButton(
                text=f"🏟 {club['name']} ({club['country']})",
                callback_data=f"select_club_{club['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return builder.as_markup()


def confirm_club_keyboard(club_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Підтвердити", callback_data=f"confirm_club_{club_id}"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="choose_club"),
    )
    return builder.as_markup()


def my_club_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👥 Склад команди", callback_data="show_squad"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return builder.as_markup()


def tactics_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for name, callback in TACTICS_LIST:
        builder.row(InlineKeyboardButton(text=name, callback_data=callback))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return builder.as_markup()


def transfers_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛒 Купити гравця", callback_data="buy_player"),
        InlineKeyboardButton(text="💰 Продати гравця", callback_data="sell_player"),
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return builder.as_markup()


def buy_players_keyboard(players: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in players[:10]:
        builder.row(
            InlineKeyboardButton(
                text=f"{p['name']} ({p['position']}) ⭐{p['rating']} — €{p['value']:,}",
                callback_data=f"buy_{p['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="transfers"))
    return builder.as_markup()


def sell_players_keyboard(players: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in players[:10]:
        builder.row(
            InlineKeyboardButton(
                text=f"{p['name']} ({p['position']}) ⭐{p['rating']} — €{p['value']:,}",
                callback_data=f"sell_{p['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="transfers"))
    return builder.as_markup()


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Головне меню", callback_data="main_menu"))
    return builder.as_markup()


def after_match_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⚽️ Ще матч", callback_data="play_match"),
        InlineKeyboardButton(text="◀️ Меню", callback_data="main_menu"),
    )
    return builder.as_markup()
