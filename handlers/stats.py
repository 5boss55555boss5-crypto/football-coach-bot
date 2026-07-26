import json

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
            "SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now', '-1 hours')"
        ) as cur:
            online_1h = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE date(last_seen) = date('now')"
        ) as cur:
            today = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now', '-7 days')"
        ) as cur:
            active_7d = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-3 days')"
        ) as cur:
            new_3d = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-7 days')"
        ) as cur:
            new_7d = (await cur.fetchone())[0]

        async with db.execute("SELECT tg_id, data FROM game_saves") as cur:
            save_rows = await cur.fetchall()

        usernames: dict[int, str] = {}
        async with db.execute("SELECT id, username FROM users") as cur:
            async for uid, uname in cur:
                usernames[uid] = uname or "Гравець"

    careers: dict[int, dict] = {}
    for tg_id, raw in save_rows:
        try:
            d = json.loads(raw)
        except Exception:
            continue
        career_log = d.get("careerLog") or []
        seasons = len(career_log)
        trophies = len(d.get("trophyHistory") or [])
        achievements = len(d.get("achievements") or {})
        club_name = None
        if career_log:
            club_name = (career_log[-1].get("club") or {}).get("name")
        if not club_name:
            club_name = f"клуб #{d.get('clubId', '?')}"

        prev = careers.get(tg_id)
        # Кожен користувач може мати до 3 слотів — беремо найпрогресованіший
        if not prev or (seasons, trophies) > (prev["seasons"], prev["trophies"]):
            careers[tg_id] = {
                "seasons": seasons,
                "trophies": trophies,
                "achievements": achievements,
                "budget": d.get("budget") or 0,
                "club": club_name,
            }

    players_active = len(careers)
    total_seasons = sum(c["seasons"] for c in careers.values())
    total_trophies = sum(c["trophies"] for c in careers.values())
    total_achievements = sum(c["achievements"] for c in careers.values())

    leaderboard = sorted(
        careers.items(),
        key=lambda kv: (kv[1]["trophies"], kv[1]["seasons"]),
        reverse=True,
    )[:5]

    def fmt_entry(tg_id, c):
        name = usernames.get(tg_id, "Гравець")
        return f"{name} — {c['club']} · {c['seasons']} сез. · 🏆{c['trophies']}"

    top_text = "\n".join(
        f"  {i + 1}. {fmt_entry(tg_id, c)}" for i, (tg_id, c) in enumerate(leaderboard)
    ) or "  — Ще ніхто не завершив сезон"

    text = (
        f"📊 <b>Статистика бота</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Всього запустили бота: <b>{total}</b>\n"
        f"🟢 Онлайн зараз (1г): <b>{online_1h}</b>\n"
        f"☀️ Заходили сьогодні: <b>{today}</b>\n"
        f"📅 Активних за 7 днів: <b>{active_7d}</b>\n"
        f"🆕 Нових за 3 дні: <b>{new_3d}</b>\n"
        f"🆕 Нових за 7 днів: <b>{new_7d}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🎮 Реально грають у грі: <b>{players_active}</b> з {total}\n"
        f"🏆 Сезонів зіграно всього: <b>{total_seasons}</b>\n"
        f"🏅 Трофеїв виграно всього: <b>{total_trophies}</b>\n"
        f"⭐ Досягнень відкрито всього: <b>{total_achievements}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 <b>Топ-5 кар'єр:</b>\n{top_text}"
    )

    await message.answer(text, parse_mode="HTML")
