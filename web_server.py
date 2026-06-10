import os
from aiohttp import web


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


def create_app():
    app = web.Application()
    app.router.add_get('/', serve_game)
    app.router.add_get('/game', serve_game)
    return app
