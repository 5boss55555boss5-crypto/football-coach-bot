from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from database.models import get_db

router = Router()

ADMIN_ID = 766751955


@router.message(Command("stat"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE date(last_seen) = date('now')"
        ) as cur:
            today = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now', '-1 hours')"
        ) as cur:
            online_1h = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-3 days')"
        ) as cur:
            new_3d = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-7 days')"
        ) as cur:
            new_7d = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now', '-7 days')"
        ) as cur:
            active_7d = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE club_id IS NOT NULL"
        ) as cur:
            with_club = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE club_id IS NULL"
        ) as cur:
            no_club = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT AVG(coach_rating) FROM users"
        ) as cur:
            avg_rating = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT MAX(coach_rating) FROM users"
        ) as cur:
            max_rating = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM matches") as cur:
            total_matches = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM matches WHERE date(played_at) = date('now')"
        ) as cur:
            matches_today = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM matches WHERE result = 'win'"
        ) as cur:
            total_wins = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM matches WHERE result = 'draw'"
        ) as cur:
            total_draws = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM matches WHERE result = 'loss'"
        ) as cur:
            total_losses = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT AVG(user_score), AVG(opponent_score) FROM matches"
        ) as cur:
            row = await cur.fetchone()
            avg_user_score = round(row[0] or 0, 1)
            avg_opp_score = round(row[1] or 0, 1)

        async with db.execute(
            """SELECT c.name, COUNT(u.id) as cnt
               FROM clubs c JOIN users u ON u.club_id = c.id
               GROUP BY c.id ORDER BY cnt DESC LIMIT 3"""
        ) as cur:
            top_clubs = await cur.fetchall()

        async with db.execute(
            """SELECT username, wins, losses, draws, coach_rating
               FROM users ORDER BY coach_rating DESC LIMIT 5"""
        ) as cur:
            top_rating = await cur.fetchall()

        async with db.execute(
            """SELECT username, wins, losses, draws, coach_rating
               FROM users ORDER BY wins DESC LIMIT 5"""
        ) as cur:
            top_wins = await cur.fetchall()

    def fmt_user(r):
        return f"{r[0] or 'Гравець'} — {r[1]}В/{r[2]}П/{r[3]}Н · ⭐{r[4]}"

    top_rating_text = "\n".join(
        f"  {i+1}. {fmt_user(r)}" for i, r in enumerate(top_rating)
    ) or "  —"

    top_wins_text = "\n".join(
        f"  {i+1}. {fmt_user(r)}" for i, r in enumerate(top_wins)
    ) or "  —"

    top_clubs_text = "\n".join(
        f"  {i+1}. {r[0]} — {r[1]} гравців" for i, r in enumerate(top_clubs)
    ) or "  —"

    winrate = round(total_wins / total_matches * 100) if total_matches else 0

    text = (
        f"📊 <b>Статистика бота</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Всього гравців: <b>{total}</b>\n"
        f"🟢 Онлайн зараз (1г): <b>{online_1h}</b>\n"
        f"☀️ Заходили сьогодні: <b>{today}</b>\n"
        f"📅 Активних за 7 днів: <b>{active_7d}</b>\n"
        f"🆕 Нових за 3 дні: <b>{new_3d}</b>\n"
        f"🆕 Нових за 7 днів: <b>{new_7d}</b>\n"
        f"⚽ Обрали клуб: <b>{with_club}</b>\n"
        f"👤 Без клубу: <b>{no_club}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🎮 Матчів всього: <b>{total_matches}</b>\n"
        f"🎯 Матчів сьогодні: <b>{matches_today}</b>\n"
        f"🏆 Перемог: <b>{total_wins}</b> · 🤝 Нічиїх: <b>{total_draws}</b> · ❌ Поразок: <b>{total_losses}</b>\n"
        f"📈 Вінрейт: <b>{winrate}%</b>\n"
        f"⚽ Середній рахунок: <b>{avg_user_score}:{avg_opp_score}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⭐ Середній рейтинг: <b>{round(avg_rating or 0)}</b>\n"
        f"👑 Макс. рейтинг: <b>{max_rating or 0}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🏟 <b>Топ клуби:</b>\n{top_clubs_text}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 <b>Топ-5 по рейтингу:</b>\n{top_rating_text}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <b>Топ-5 по перемогах:</b>\n{top_wins_text}"
    )

    await message.answer(text, parse_mode="HTML")
