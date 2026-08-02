import logging
import os

from aiohttp import web

from database.models import get_db

logger = logging.getLogger(__name__)

ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "766751955"))
NOTIFY_TEXT_MAX_LEN = 4000
CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()
SUBSCRIBED_STATUSES = {"member", "administrator", "creator"}
SAVE_DATA_MAX_LEN = 4_000_000


async def serve_game(request):
    path = os.path.join(os.path.dirname(__file__), 'game.html')
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    return web.Response(
        body=content.encode('utf-8'),
        content_type='text/html',
        charset='utf-8',
        headers={
            "ngrok-skip-browser-warning": "1",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


async def notify(request):
    bot = request.app.get("bot")
    if bot is None:
        return web.json_response({"ok": False, "error": "bot not ready"}, status=503)

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid json"}, status=400)

    text = str(data.get("text") or "").strip()[:NOTIFY_TEXT_MAX_LEN]
    if not text:
        return web.json_response({"ok": False, "error": "empty text"}, status=400)

    try:
        await bot.send_message(chat_id=ADMIN_TG_ID, text=text, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Failed to deliver game notification to admin: {e}")
        return web.json_response({"ok": False}, status=502)

    return web.json_response({"ok": True})


async def check_subscription(request):
    bot = request.app.get("bot")
    if bot is None:
        return web.json_response({"ok": False, "error": "bot not ready"}, status=503)
    if not CHANNEL_ID:
        return web.json_response({"ok": False, "error": "channel not configured"}, status=503)

    try:
        data = await request.json()
        user_id = int(data.get("user_id"))
    except Exception:
        return web.json_response({"ok": False, "error": "invalid request"}, status=400)

    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        subscribed = member.status in SUBSCRIBED_STATUSES
    except Exception as e:
        logger.info(f"check_subscription: user {user_id} not found in channel or error: {e}")
        subscribed = False

    return web.json_response({"ok": True, "subscribed": subscribed})


async def save_game(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id"))
        slot = int(data.get("slot"))
        payload = data.get("data")
    except Exception:
        return web.json_response({"ok": False, "error": "invalid request"}, status=400)

    if slot not in (1, 2, 3) or not isinstance(payload, str) or not payload:
        return web.json_response({"ok": False, "error": "invalid payload"}, status=400)
    if len(payload) > SAVE_DATA_MAX_LEN:
        return web.json_response({"ok": False, "error": "payload too large"}, status=413)

    try:
        async with get_db() as db:
            await db.execute(
                """INSERT INTO game_saves (tg_id, slot, data, updated_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(tg_id, slot) DO UPDATE SET data=excluded.data, updated_at=CURRENT_TIMESTAMP""",
                (user_id, slot, payload),
            )
            await db.commit()
    except Exception as e:
        logger.warning(f"save_game failed for user {user_id} slot {slot}: {e}")
        return web.json_response({"ok": False}, status=500)

    return web.json_response({"ok": True})


async def load_game(request):
    try:
        user_id = int(request.query.get("user_id"))
        slot = int(request.query.get("slot"))
    except Exception:
        return web.json_response({"ok": False, "error": "invalid request"}, status=400)

    try:
        async with get_db() as db:
            async with db.execute(
                "SELECT data FROM game_saves WHERE tg_id = ? AND slot = ?", (user_id, slot)
            ) as cursor:
                row = await cursor.fetchone()
    except Exception as e:
        logger.warning(f"load_game failed for user {user_id} slot {slot}: {e}")
        return web.json_response({"ok": False}, status=500)

    return web.json_response({"ok": True, "data": row[0] if row else None})


async def active_slot(request):
    try:
        user_id = int(request.query.get("user_id"))
    except Exception:
        return web.json_response({"ok": False, "error": "invalid request"}, status=400)

    try:
        async with get_db() as db:
            async with db.execute(
                "SELECT slot FROM game_saves WHERE tg_id = ? ORDER BY updated_at DESC LIMIT 1",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
    except Exception as e:
        logger.warning(f"active_slot failed for user {user_id}: {e}")
        return web.json_response({"ok": False}, status=500)

    return web.json_response({"ok": True, "slot": row[0] if row else None})


def create_app(bot=None):
    app = web.Application(client_max_size=SAVE_DATA_MAX_LEN + 1024)
    app["bot"] = bot
    app.router.add_get('/', serve_game)
    app.router.add_get('/game', serve_game)
    app.router.add_post('/api/notify', notify)
    app.router.add_post('/api/check-subscription', check_subscription)
    app.router.add_post('/api/save-game', save_game)
    app.router.add_get('/api/load-game', load_game)
    app.router.add_get('/api/active-slot', active_slot)
    app.router.add_static(
        '/identity_v2_assets/',
        path=os.path.join(os.path.dirname(__file__), 'identity_v2_assets'),
        show_index=False,
    )
    return app
