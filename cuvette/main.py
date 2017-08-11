from pathlib import Path

from aiohttp import web

from .settings import Settings
from .views import index


THIS_DIR = Path(__file__).parent
BASE_DIR = THIS_DIR.parent


async def startup(app: web.Application):
    pass


async def cleanup(app: web.Application):
    pass


def setup_routes(app):
    app.router.add_get('/', index, name='index')


def create_app(loop):
    app = web.Application()
    settings = Settings()
    app.update(
        name='cuvette',
        settings=settings
    )

    app.on_startup.append(startup)
    app.on_cleanup.append(cleanup)

    setup_routes(app)
    return app
