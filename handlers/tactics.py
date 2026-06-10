from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.keyboards import tactics_keyboard, main_menu_keyboard, TACTICS_NAMES
from database.models import get_db

router = Router()


@router.callback_query(F.data == "tactics")
async def show_tactics(callback: CallbackQuery):
    async with get_db() as db:
        async with db.execute("SELECT club_id, tactics FROM users WHERE id = ?", (callback.from_user.id,)) as cursor:
            user = await cursor.fetchone()

    if not user or not user[0]:
        await callback.answer("❌ Спочатку обери клуб!", show_alert=True)
        return

    current = TACTICS_NAMES.get(user[1], user[1])

    await callback.message.edit_text(
        f"🧠 <b>Тактика</b>\n\nПоточна: <b>{current}</b>\n\nОбери нову тактику:\n\n"
        f"🔥 <b>Атакувальна</b> — +5, ризикована\n"
        f"🧱 <b>Захисна</b> — +2, надійна\n"
        f"⚖️ <b>Збалансована</b> — +3, рівномірна\n"
        f"⚡️ <b>Контратаки</b> — +4, швидкі переходи\n"
        f"🎯 <b>Високий пресинг</b> — +4, агресивна\n"
        f"🧠 <b>Контроль м'яча</b> — +3, позиційна\n",
        reply_markup=tactics_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tactic_"))
async def set_tactic(callback: CallbackQuery):
    async with get_db() as db:
        async with db.execute("SELECT club_id FROM users WHERE id = ?", (callback.from_user.id,)) as cursor:
            user = await cursor.fetchone()

        if not user or not user[0]:
            await callback.answer("❌ Спочатку обери клуб!", show_alert=True)
            return

        await db.execute("UPDATE users SET tactics = ? WHERE id = ?", (callback.data, callback.from_user.id))
        await db.commit()

    name = TACTICS_NAMES.get(callback.data, callback.data)
    await callback.message.edit_text(
        f"✅ Тактику встановлено: <b>{name}</b>\n\nКоманда готова до матчу!",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
