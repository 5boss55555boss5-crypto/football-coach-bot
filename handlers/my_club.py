from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.keyboards import my_club_keyboard, back_to_main_keyboard, TACTICS_NAMES
from database.models import get_db

router = Router()


@router.callback_query(F.data == "my_club")
async def my_club(callback: CallbackQuery):
    user_id = callback.from_user.id

    async with get_db() as db:
        async with db.execute(
            """SELECT u.budget, u.tactics, u.wins, u.losses, u.draws, u.coach_rating, c.name, c.team_strength
               FROM users u LEFT JOIN clubs c ON u.club_id = c.id WHERE u.id = ?""",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if not row or not row[6]:
            await callback.answer("❌ Спочатку обери клуб!", show_alert=True)
            return

        async with db.execute(
            """SELECT p.name, p.position, p.rating FROM user_players up
               JOIN players p ON up.player_id = p.id WHERE up.user_id = ? ORDER BY p.rating DESC""",
            (user_id,)
        ) as cursor:
            players = await cursor.fetchall()

    tactic_name = TACTICS_NAMES.get(row[1], row[1])
    total = row[2] + row[3] + row[4]
    avg_rating = sum(p[2] for p in players) / len(players) if players else 0

    text = (
        f"🏟 <b>{row[6]}</b>\n\n"
        f"💰 Бюджет: €{row[0]:,}\n"
        f"💪 Сила команди: {row[7]}/100\n"
        f"⭐️ Сер. рейтинг: {avg_rating:.1f}\n"
        f"🧠 Тактика: {tactic_name}\n"
        f"📊 Рейтинг тренера: {row[5]}\n\n"
        f"📋 Матчів: {total} | ✅ {row[2]} | 🤝 {row[4]} | ❌ {row[3]}\n\n"
        f"👥 <b>Склад ({len(players)} гравців):</b>\n"
    )

    for p in players[:11]:
        emoji = {"ВРТ": "🧤", "ЗАХ": "🔴", "ПВ": "🔵", "НАП": "⚡️"}.get(p[1], "⚽")
        text += f"  {emoji} {p[0]} ({p[1]}) ⭐{p[2]}\n"

    if len(players) > 11:
        text += f"  ...ще {len(players) - 11} гравців\n"

    await callback.message.edit_text(text, reply_markup=my_club_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "show_squad")
async def show_squad(callback: CallbackQuery):
    async with get_db() as db:
        async with db.execute(
            """SELECT p.name, p.position, p.rating, p.value, p.salary
               FROM user_players up JOIN players p ON up.player_id = p.id
               WHERE up.user_id = ?
               ORDER BY CASE p.position WHEN 'ВРТ' THEN 1 WHEN 'ЗАХ' THEN 2 WHEN 'ПВ' THEN 3 WHEN 'НАП' THEN 4 END, p.rating DESC""",
            (callback.from_user.id,)
        ) as cursor:
            players = await cursor.fetchall()

    if not players:
        await callback.answer("❌ У тебе немає гравців!", show_alert=True)
        return

    lines = ["👥 <b>Повний склад:</b>\n"]
    current_pos = None

    for p in players:
        if p[1] != current_pos:
            current_pos = p[1]
            label = {"ВРТ": "🧤 Воротарі", "ЗАХ": "🔴 Захисники", "ПВ": "🔵 Півзахисники", "НАП": "⚡️ Нападники"}.get(p[1], p[1])
            lines.append(f"\n<b>{label}</b>")
        lines.append(f"  • {p[0]} ⭐{p[2]} | €{p[3]:,} | €{p[4]:,}/міс")

    await callback.message.edit_text("\n".join(lines), reply_markup=back_to_main_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "stats")
async def show_stats(callback: CallbackQuery):
    user_id = callback.from_user.id

    async with get_db() as db:
        async with db.execute("SELECT wins, losses, draws, coach_rating FROM users WHERE id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()

        async with db.execute(
            """SELECT user_club, opponent_club, user_score, opponent_score, result, prize_money
               FROM matches WHERE user_id = ? ORDER BY played_at DESC LIMIT 5""",
            (user_id,)
        ) as cursor:
            matches = await cursor.fetchall()

    if not user:
        await callback.answer("❌ Гравця не знайдено!", show_alert=True)
        return

    wins, losses, draws, rating = user
    total = wins + losses + draws
    win_rate = (wins / total * 100) if total > 0 else 0

    text = (
        f"📊 <b>Статистика тренера</b>\n\n"
        f"🏆 Рейтинг: {rating}\n"
        f"📋 Матчів: {total} | ✅ {wins} | 🤝 {draws} | ❌ {losses}\n"
        f"📈 Відсоток перемог: {win_rate:.1f}%\n"
    )

    if matches:
        text += "\n📋 <b>Останні матчі:</b>\n"
        for m in matches:
            icon = {"win": "✅", "draw": "🤝", "loss": "❌"}.get(m[4], "❓")
            text += f"  {icon} {m[0]} {m[2]}:{m[3]} {m[1]} | €{m[5]:,}\n"

    await callback.message.edit_text(text, reply_markup=back_to_main_keyboard(), parse_mode="HTML")
    await callback.answer()
