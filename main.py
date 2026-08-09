import asyncio
import html
import logging
import os
import time
from datetime import datetime, timedelta

from aiohttp import web
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from database.models import init_db, get_db
from database.seeder import seed_database
from handlers import start, clubs, my_club, tactics, match, transfers, ranking, stats
from keyboards.keyboards import main_menu_keyboard
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


async def cmd_whatchat(message: Message) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    fwd = message.forward_from_chat
    if not fwd:
        await message.answer("Переслав не з каналу — forward_from_chat порожній.")
        return
    await message.answer(
        f"📌 Chat ID: <code>{fwd.id}</code>\n"
        f"Назва: {html.escape(fwd.title or '')}\n"
        f"Тип: {fwd.type}",
        parse_mode="HTML",
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


INACTIVITY_CHECK_INTERVAL = 6 * 3600  # how often to scan for inactive players
INACTIVITY_MIN_IDLE = timedelta(hours=20)   # don't nudge someone who played today
INACTIVITY_MAX_IDLE = timedelta(days=14)    # stop nudging long-abandoned accounts
INACTIVITY_REMINDER_COOLDOWN = timedelta(days=3)  # don't repeat too often


async def inactivity_reminder_loop(bot: Bot):
    """Nudges players who've gone quiet to come back — the only notification
    the game can send that isn't tied to the in-game clock (which only moves
    while someone is actually playing), so it's the one case a server-side
    reminder actually makes sense."""
    kb = main_menu_keyboard()
    while True:
        try:
            now = datetime.utcnow()
            async with get_db() as db:
                async with db.execute(
                    "SELECT tg_id, MAX(updated_at) FROM game_saves GROUP BY tg_id"
                ) as cursor:
                    rows = await cursor.fetchall()

                for tg_id, last_active_raw in rows:
                    try:
                        idle_for = now - datetime.fromisoformat(last_active_raw)
                    except (TypeError, ValueError):
                        continue
                    if not (INACTIVITY_MIN_IDLE <= idle_for <= INACTIVITY_MAX_IDLE):
                        continue

                    async with db.execute(
                        "SELECT last_reminded_at FROM inactivity_reminders WHERE tg_id = ?", (tg_id,)
                    ) as cursor2:
                        row = await cursor2.fetchone()
                    if row:
                        try:
                            if now - datetime.fromisoformat(row[0]) < INACTIVITY_REMINDER_COOLDOWN:
                                continue
                        except (TypeError, ValueError):
                            pass

                    try:
                        await bot.send_message(
                            chat_id=tg_id,
                            text="⚽ Твій клуб сумує без тебе! Матчі, трансфери й новий сезон чекають — час повертатись на лаву тренера.",
                            reply_markup=kb,
                        )
                        await db.execute(
                            "INSERT INTO inactivity_reminders (tg_id, last_reminded_at) VALUES (?, ?) "
                            "ON CONFLICT(tg_id) DO UPDATE SET last_reminded_at = excluded.last_reminded_at",
                            (tg_id, now.isoformat()),
                        )
                        await db.commit()
                    except Exception as e:
                        logger.info(f"inactivity reminder skipped for {tg_id}: {e}")
                    await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"inactivity_reminder_loop error: {e}")
        await asyncio.sleep(INACTIVITY_CHECK_INTERVAL)


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
    dp.message.register(cmd_whatchat, F.forward_from_chat)
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

    asyncio.create_task(inactivity_reminder_loop(bot))

    logger.info("🤖 Бот запускається...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
