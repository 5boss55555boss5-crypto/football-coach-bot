from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.keyboards import after_match_keyboard
from database.models import get_db
from utils.match_engine import simulate_match, format_match_result

router = Router()


@router.callback_query(F.data == "play_match")
async def play_match(callback: CallbackQuery):
    user_id = callback.from_user.id

    async with get_db() as db:
        async with db.execute(
            """SELECT u.budget, u.tactics, u.wins, u.losses, u.draws, u.coach_rating, c.name
               FROM users u LEFT JOIN clubs c ON u.club_id = c.id WHERE u.id = ?""",
            (user_id,)
        ) as cursor:
            user = await cursor.fetchone()

        if not user or not user[6]:
            await callback.answer("❌ Спочатку обери клуб!", show_alert=True)
            return

        budget, tactics, wins, losses, draws, coach_rating, club_name = user

        async with db.execute(
            """SELECT p.name, p.position, p.rating FROM user_players up
               JOIN players p ON up.player_id = p.id WHERE up.user_id = ?""",
            (user_id,)
        ) as cursor:
            players = [{"name": r[0], "position": r[1], "rating": r[2]} for r in await cursor.fetchall()]

    match = simulate_match(players, tactics, club_name)

    if match["result"] == "win":
        new_wins, new_losses, new_draws, rating_change = wins + 1, losses, draws, +15
    elif match["result"] == "draw":
        new_wins, new_losses, new_draws, rating_change = wins, losses, draws + 1, +3
    else:
        new_wins, new_losses, new_draws, rating_change = wins, losses + 1, draws, -10

    new_budget = budget + match["prize"]
    new_rating = max(0, coach_rating + rating_change)

    async with get_db() as db:
        await db.execute(
            "UPDATE users SET budget = ?, wins = ?, losses = ?, draws = ?, coach_rating = ? WHERE id = ?",
            (new_budget, new_wins, new_losses, new_draws, new_rating, user_id)
        )
        await db.execute(
            "INSERT INTO matches (user_id, user_club, opponent_club, user_score, opponent_score, result, prize_money) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, club_name, match["opponent_name"], match["user_goals"], match["opp_goals"], match["result"], match["prize"])
        )
        await db.commit()

    sign = "+" if rating_change >= 0 else ""
    text = format_match_result(match, club_name)
    text += f"\n📊 Рейтинг: {coach_rating} → {new_rating} ({sign}{rating_change})"
    text += f"\n💼 Бюджет: €{budget:,} → €{new_budget:,}"

    await callback.message.edit_text(text, reply_markup=after_match_keyboard())
    await callback.answer()
