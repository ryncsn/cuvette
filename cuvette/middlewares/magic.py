"""
Middleware and utils handling special logics.

Let's just call thoese rules magic before anyone comes up with a
better idea.
"""
import typing
import json
import uuid

from aiohttp_session import get_session
from cuvette.machine import Machine


def random_key():
    """
    This key will get exposed and not likely to collision,
    as we will only have a few hundreds of machines
    so use uuid4 for security reason.
    """
    return str(uuid.uuid4())


class Magic(object):
    """
    One magic object for one request

    Wrap all hack and implicit there there
    """
    def __init__(self, request):
        self.request = request

    async def get_session(self):
        self.session = await get_session(self.request)

    async def pre_query(self, params: dict):
        """
        If the user (Idendified by Cookie) is requesting/querying with same parameter,
        just return the machine he just requested, to prevent span.

        Unless the user request with param 'magic' = 'new'
        """
        magic = params.pop('magic', None)

        if magic == 'new':
            return None

        request_hash = hash(json.dumps(params, sort_keys=True))
        last_request_hash = self.session.setdefault('last_request_hash', request_hash)
        last_machine_magics = self.session.get('last_machine_magics')

        if request_hash == last_request_hash and last_machine_magics:
            machines = await Machine.find_all(self.request.app['db'], {
                'magic': {
                    '$in': last_machine_magics
                }
            })
            if machines:
                return machines

        if isinstance(magic, str):
            params['magic'] = magic

        return None

    pre_request = pre_query

    async def pre_provision(self, machines: typing.List[Machine], query: dict):
        """
        Before provision, checking if provision is allowed and if allowed
        remember the current provision parameters (use hash).
        """
        self.session['last_machine_magics'] = []
        for machine in machines:
            magic = machine['magic'] = machine['magic'] or random_key()
            self.session['last_machine_magics'].append(magic)

    async def allow_provision(self, query: dict):
        """
        Before provision, checking if provision is allowed and if allowed
        remember the current provision parameters (use hash).
        """
        if query.get('magic') == 'noprovision':
            return False
        return True


async def middleware(app, handler):
    async def magic_handler(request):
        await request.setdefault('magic', Magic(request)).get_session()
        return await(handler(request))
    return magic_handler
