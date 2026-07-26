import logging
import os

from aiohttp import web

logger = logging.getLogger(__name__)

ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "766751955"))
NOTIFY_TEXT_MAX_LEN = 4000
CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()
SUBSCRIBED_STATUSES = {"member", "administrator", "creator"}


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


def create_app(bot=None):
    app = web.Application()
    app["bot"] = bot
    app.router.add_get('/', serve_game)
    app.router.add_get('/game', serve_game)
    app.router.add_post('/api/notify', notify)
    app.router.add_post('/api/check-subscription', check_subscription)
    return app
