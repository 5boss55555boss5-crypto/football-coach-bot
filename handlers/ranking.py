from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.keyboards import back_to_main_keyboard
from database.models import get_db

router = Router()


@router.callback_query(F.data == "ranking")
async def show_ranking(callback: CallbackQuery):
    async with get_db() as db:
        async with db.execute(
            """SELECT u.username, c.name, u.wins, u.budget, u.coach_rating
               FROM users u LEFT JOIN clubs c ON u.club_id = c.id
               WHERE u.club_id IS NOT NULL
               ORDER BY u.coach_rating DESC, u.wins DESC LIMIT 10"""
        ) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await callback.message.edit_text(
            "🏆 <b>Рейтинг тренерів</b>\n\nПоки що порожньо. Зіграй перший матч!",
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>Топ тренерів</b>\n"]

    for i, (username, club, wins, budget, rating) in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = f"@{username}" if username else "Анонім"
        lines.append(f"{medal} {name}\n   🏟 {club or 'Без клубу'} | ✅ {wins} | ⭐ {rating} | €{budget:,}\n")

    await callback.message.edit_text("\n".join(lines), reply_markup=back_to_main_keyboard(), parse_mode="HTML")
    await callback.answer()
