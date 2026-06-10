import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from keyboards.keyboards import main_menu_keyboard
from database.models import get_db

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message):
    try:
        async with get_db() as db:
            async with db.execute("SELECT id FROM users WHERE id = ?", (message.from_user.id,)) as cursor:
                user = await cursor.fetchone()
            if not user:
                await db.execute(
                    "INSERT INTO users (id, username) VALUES (?, ?)",
                    (message.from_user.id, message.from_user.username or "Гравець")
                )
            else:
                await db.execute(
                    "UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE id = ?",
                    (message.from_user.id,)
                )
            await db.commit()
    except Exception as e:
        logger.error(f"DB error in cmd_start for user {message.from_user.id}: {e}")

    try:
        kb = main_menu_keyboard()
    except Exception as e:
        logger.error(f"Keyboard error in cmd_start: {e}")
        kb = None

    try:
        await message.answer(
            "🏆 <b>Футбольний Менеджер</b>\n\n"
            "Стань головним тренером топ-клубу та доведи команду до чемпіонства!\n\n"
            "⚽ Живі матчі · 🔄 Трансфери · 🧠 Тактика · 🏆 Кубок",
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Answer error in cmd_start: {e}")
        await message.answer("Бот працює! Спробуй ще раз /start")


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    try:
        kb = main_menu_keyboard()
    except Exception as e:
        logger.error(f"Keyboard error in main_menu callback: {e}")
        kb = None
    await callback.message.edit_text(
        "🏆 <b>Футбольний Менеджер</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()
