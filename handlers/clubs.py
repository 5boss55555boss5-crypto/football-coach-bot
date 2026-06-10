from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.keyboards import clubs_keyboard, confirm_club_keyboard, main_menu_keyboard
from database.models import get_db

router = Router()


@router.callback_query(F.data == "choose_club")
async def choose_club(callback: CallbackQuery):
    async with get_db() as db:
        async with db.execute("SELECT id, name, budget, team_strength, country FROM clubs") as cursor:
            clubs = [{"id": r[0], "name": r[1], "budget": r[2], "team_strength": r[3], "country": r[4]}
                     for r in await cursor.fetchall()]

    await callback.message.edit_text(
        "🏟 <b>Вибір клубу</b>\n\nОбери команду для своєї кар'єри тренера:",
        reply_markup=clubs_keyboard(clubs),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("select_club_"))
async def select_club(callback: CallbackQuery):
    club_id = int(callback.data.split("_")[-1])

    async with get_db() as db:
        async with db.execute(
            "SELECT id, name, budget, team_strength, country FROM clubs WHERE id = ?", (club_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            await callback.answer("Клуб не знайдено!", show_alert=True)
            return

        club = {"id": row[0], "name": row[1], "budget": row[2], "team_strength": row[3], "country": row[4]}

        async with db.execute(
            "SELECT name, position, rating FROM players WHERE club_id = ? ORDER BY rating DESC LIMIT 5",
            (club_id,)
        ) as cursor:
            players = await cursor.fetchall()

    players_text = "\n".join([f"  • {p[0]} ({p[1]}) ⭐{p[2]}" for p in players])

    await callback.message.edit_text(
        f"🏟 <b>{club['name']}</b> ({club['country']})\n\n"
        f"💰 Бюджет: €{club['budget']:,}\n"
        f"💪 Сила команди: {club['team_strength']}/100\n\n"
        f"⭐️ Топ гравці:\n{players_text}\n\n"
        f"Підтвердити вибір цього клубу?",
        reply_markup=confirm_club_keyboard(club_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_club_"))
async def confirm_club(callback: CallbackQuery):
    club_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id

    async with get_db() as db:
        async with db.execute("SELECT name, budget FROM clubs WHERE id = ?", (club_id,)) as cursor:
            club = await cursor.fetchone()

        if not club:
            await callback.answer("Клуб не знайдено!", show_alert=True)
            return

        await db.execute(
            "UPDATE users SET club_id = ?, budget = ?, wins = 0, losses = 0, draws = 0, tactics = 'tactic_balanced' WHERE id = ?",
            (club_id, club[1], user_id)
        )
        await db.execute("DELETE FROM user_players WHERE user_id = ?", (user_id,))

        async with db.execute("SELECT id FROM players WHERE club_id = ?", (club_id,)) as cursor:
            player_ids = [r[0] for r in await cursor.fetchall()]

        for pid in player_ids:
            await db.execute("INSERT INTO user_players (user_id, player_id) VALUES (?, ?)", (user_id, pid))

        await db.commit()

    await callback.message.edit_text(
        f"✅ Чудово! Ти обрав <b>{club[0]}</b>!\n\n"
        f"Твоя кар'єра тренера починається. Удачі! 🍀\n\n"
        f"💰 Стартовий бюджет: €{club[1]:,}",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
