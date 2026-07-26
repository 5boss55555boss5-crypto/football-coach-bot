import asyncio
import html
import logging
import os
import time

from aiohttp import web
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from database.models import init_db, get_db
from database.seeder import seed_database
from handlers import start, clubs, my_club, tactics, match, transfers, ranking, stats
from web_server import create_app

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "766751955"))
PENDING_BROADCASTS: dict[str, str] = {}


class UserStatsMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message) and event.from_user:
            try:
                async with get_db() as db:
                    await db.execute(
                        "UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE id = ?",
                        (event.from_user.id,)
                    )
                    await db.commit()
            except Exception:
                pass
        return await handler(event, data)


def _is_admin(user_id: int | None) -> bool:
    return user_id == ADMIN_TG_ID


async def cmd_mmm(message: Message) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        await message.answer("⛔ Команда /mmm доступна тільки адміну.")
        return

    text = (message.text or "").split(maxsplit=1)
    if len(text) < 2 or not text[1].strip():
        await message.answer("Напиши так: /mmm Вийшло оновлення гри 🎮")
        return

    broadcast_text = text[1].strip()
    confirm_id = f"{int(time.time())}_{message.from_user.id}"
    PENDING_BROADCASTS[confirm_id] = broadcast_text

    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            users_count = (await cursor.fetchone())[0]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Надіслати", callback_data=f"mmm_confirm:{confirm_id}"),
        InlineKeyboardButton(text="❌ Скасувати", callback_data=f"mmm_cancel:{confirm_id}"),
    ]])

    await message.answer(
        "📣 <b>Підтвердити розсилку?</b>\n\n"
        f"<b>Текст:</b>\n{html.escape(broadcast_text)}\n\n"
        f"Отримувачів у базі: <b>{users_count}</b>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def cb_mmm(callback: CallbackQuery, bot: Bot) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None):
        await callback.answer("Тільки адмін", show_alert=True)
        return

    action, _, confirm_id = (callback.data or "").partition(":")
    text = PENDING_BROADCASTS.pop(confirm_id, None)
    if not text:
        await callback.answer("Ця розсилка вже неактивна", show_alert=True)
        return

    if action == "mmm_cancel":
        await callback.answer("Скасовано")
        if callback.message:
            await callback.message.edit_text("❌ Розсилку скасовано.")
        return

    async with get_db() as db:
        async with db.execute("SELECT id FROM users") as cursor:
            user_ids = [r[0] for r in await cursor.fetchall()]

    ok = 0
    fail = 0

    await callback.answer("Надсилаю...")
    if callback.message:
        await callback.message.edit_text(
            f"📣 Розсилка запущена. Отримувачів: <b>{len(user_ids)}</b>",
            parse_mode="HTML",
        )

    for uid in user_ids:
        try:
            await bot.send_message(chat_id=uid, text=text)
            ok += 1
            await asyncio.sleep(0.04)
        except Exception:
            fail += 1

    await bot.send_message(
        chat_id=ADMIN_TG_ID,
        text=f"✅ Розсилку завершено. Доставлено: {ok}, помилок: {fail}",
    )


async def run_web_server(bot: Bot):
    port = int(os.getenv("PORT") or os.getenv("WEB_PORT", "8080"))
    app = create_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 Веб-сервер запущено на порту {port}")

    if not os.getenv("WEB_URL"):
        logger.warning("⚠️ WEB_URL не задано. Постав WEB_URL в Railway Variables.")


async def main():
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("❌ BOT_TOKEN не знайдено! Перевір .env файл.")

    bot = Bot(token=bot_token)
    dp = Dispatcher()
    dp.message.middleware(UserStatsMiddleware())
    dp.message.register(cmd_mmm, Command("mmm"))
    dp.callback_query.register(cb_mmm, F.data.startswith("mmm_"))

    dp.include_router(start.router)
    dp.include_router(clubs.router)
    dp.include_router(my_club.router)
    dp.include_router(tactics.router)
    dp.include_router(match.router)
    dp.include_router(transfers.router)
    dp.include_router(ranking.router)
    dp.include_router(stats.router)

    logger.info("Ініціалізація бази даних...")
    await init_db()
    await seed_database()

    await run_web_server(bot)

    logger.info("🤖 Бот запускається...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
