from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.keyboards import transfers_keyboard, buy_players_keyboard, sell_players_keyboard, back_to_main_keyboard
from database.models import get_db

router = Router()


@router.callback_query(F.data == "transfers")
async def transfers_menu(callback: CallbackQuery):
    async with get_db() as db:
        async with db.execute("SELECT club_id, budget FROM users WHERE id = ?", (callback.from_user.id,)) as cursor:
            user = await cursor.fetchone()

    if not user or not user[0]:
        await callback.answer("❌ Спочатку обери клуб!", show_alert=True)
        return

    await callback.message.edit_text(
        f"🔄 <b>Трансферний ринок</b>\n\n💰 Бюджет: €{user[1]:,}\n\nКупуй або продавай гравців:",
        reply_markup=transfers_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "buy_player")
async def show_buy_players(callback: CallbackQuery):
    user_id = callback.from_user.id

    async with get_db() as db:
        async with db.execute("SELECT budget FROM users WHERE id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()

        async with db.execute(
            """SELECT p.id, p.name, p.position, p.rating, p.value, p.salary FROM players p
               WHERE p.id NOT IN (SELECT player_id FROM user_players WHERE user_id = ?)
               AND (p.is_free_agent = 1 OR p.club_id IS NOT NULL)
               ORDER BY p.rating DESC LIMIT 20""",
            (user_id,)
        ) as cursor:
            players = [{"id": r[0], "name": r[1], "position": r[2], "rating": r[3], "value": r[4], "salary": r[5]}
                       for r in await cursor.fetchall()]

    await callback.message.edit_text(
        f"🛒 <b>Доступні гравці</b>\n\n💰 Бюджет: €{user[0]:,}\n\nОберіть гравця:",
        reply_markup=buy_players_keyboard(players),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_"))
async def buy_player(callback: CallbackQuery):
    player_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    async with get_db() as db:
        async with db.execute("SELECT budget, club_id FROM users WHERE id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()

        async with db.execute("SELECT name, value, position, rating FROM players WHERE id = ?", (player_id,)) as cursor:
            player = await cursor.fetchone()

        async with db.execute("SELECT id FROM user_players WHERE user_id = ? AND player_id = ?", (user_id, player_id)) as cursor:
            existing = await cursor.fetchone()

        if not user or not user[1] or not player:
            await callback.answer("❌ Помилка!", show_alert=True)
            return

        if existing:
            await callback.answer("❌ Гравець вже є у складі!", show_alert=True)
            return

        if user[0] < player[1]:
            await callback.answer(f"❌ Недостатньо коштів! Потрібно €{player[1]:,}, є €{user[0]:,}", show_alert=True)
            return

        new_budget = user[0] - player[1]
        await db.execute("UPDATE users SET budget = ? WHERE id = ?", (new_budget, user_id))
        await db.execute("INSERT INTO user_players (user_id, player_id) VALUES (?, ?)", (user_id, player_id))
        await db.commit()

    await callback.message.edit_text(
        f"✅ <b>Трансфер завершено!</b>\n\n<b>{player[0]}</b> ({player[2]}, ⭐{player[3]}) у своєму складі.\n\n"
        f"💰 Витрачено: €{player[1]:,}\n💼 Залишок: €{new_budget:,}",
        reply_markup=back_to_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "sell_player")
async def show_sell_players(callback: CallbackQuery):
    async with get_db() as db:
        async with db.execute(
            """SELECT p.id, p.name, p.position, p.rating, p.value FROM user_players up
               JOIN players p ON up.player_id = p.id WHERE up.user_id = ? ORDER BY p.value DESC""",
            (callback.from_user.id,)
        ) as cursor:
            players = [{"id": r[0], "name": r[1], "position": r[2], "rating": r[3], "value": r[4]}
                       for r in await cursor.fetchall()]

    if not players:
        await callback.answer("❌ Немає гравців для продажу!", show_alert=True)
        return

    await callback.message.edit_text(
        "💰 <b>Продаж гравців</b>\n\nОбери гравця для продажу:",
        reply_markup=sell_players_keyboard(players),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sell_"))
async def sell_player(callback: CallbackQuery):
    player_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    async with get_db() as db:
        async with db.execute("SELECT budget FROM users WHERE id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()

        async with db.execute("SELECT name, value, position, rating FROM players WHERE id = ?", (player_id,)) as cursor:
            player = await cursor.fetchone()

        async with db.execute("SELECT id FROM user_players WHERE user_id = ? AND player_id = ?", (user_id, player_id)) as cursor:
            ownership = await cursor.fetchone()

        if not player or not user or not ownership:
            await callback.answer("❌ Помилка!", show_alert=True)
            return

        sell_price = int(player[1] * 0.8)
        new_budget = user[0] + sell_price
        await db.execute("UPDATE users SET budget = ? WHERE id = ?", (new_budget, user_id))
        await db.execute("DELETE FROM user_players WHERE user_id = ? AND player_id = ?", (user_id, player_id))
        await db.commit()

    await callback.message.edit_text(
        f"✅ <b>Гравця продано!</b>\n\n<b>{player[0]}</b> ({player[2]}, ⭐{player[3]}) покинув клуб.\n\n"
        f"💰 Отримано: €{sell_price:,} (80%)\n💼 Бюджет: €{new_budget:,}",
        reply_markup=back_to_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
