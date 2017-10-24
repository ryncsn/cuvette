import base64
import logging
import asyncio

from pathlib import Path
from cryptography import fernet

from aiohttp import web
from aiohttp_session import setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage

from cuvette.middlewares import Middlewares
from cuvette.settings import Settings
from cuvette.pool import setup as pool_setup
from cuvette.views import index, parameters, provisioners, MachineView
from cuvette.views.callbacks import tear_me_down, describ_me, release_me


THIS_DIR = Path(__file__).parent
BASE_DIR = THIS_DIR.parent


async def startup(app: web.Application):
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('cuvette')
    logger.setLevel(logging.INFO)
    logger.info("Info Cuvette starting...")
    pool_setup(asyncio.get_event_loop(), app)


async def cleanup(app: web.Application):
    pass


def setup_routes(app):
    app.router.add_get('/', index, name='index')
    app.router.add_get('/parameters', parameters, name='parameters')
    app.router.add_get('/provisioners', provisioners, name='provisioners')
    app.router.add_get('/machines', MachineView.get, name='machine_get')
    app.router.add_post('/machines', MachineView.post, name='machine_post')
    app.router.add_delete('/machines', MachineView.delete, name='machine_delete')
    app.router.add_get('/machines/request', MachineView.request, name='machine_request')
    app.router.add_post('/machines/request', MachineView.request, name='machine_request_post')
    app.router.add_post('/machines/provision', MachineView.provision, name='machine_provision')
    app.router.add_post('/machines/teardown', MachineView.teardown, name='machine_teardown')

    app.router.add_get('/release_me', release_me, name='release_me')
    app.router.add_get('/describ_me', describ_me, name='describ_me')
    app.router.add_get('/tear_me_down', tear_me_down, name='tear_me_down')


def create_app(loop):
    app = web.Application()
    settings = Settings()
    app.update(
        name='cuvette',
        settings=settings,
    )

    app.on_startup.append(startup)
    app.on_cleanup.append(cleanup)

    # secret_key must be 32 url-safe base64-encoded bytes
    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)

    setup(app, EncryptedCookieStorage(secret_key))

    app.middlewares.extend(Middlewares)

    setup_routes(app)
    return app
