"""
Middleware and utils handling special logics.

Let's just call thoese rules magic before anyone comes up with a
better idea.
"""

import json
import uuid

from aiohttp_session import get_session
from cuvette.pool.machine import Machine


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
    async def __init__(self, request):
        self.request = request
        self.session = await get_session(request)

    async def pre_query(self, params: dict):
        """
        If the user (Idendified by Cookie) is requesting/querying with same parameter,
        just return the machine he just requested, to prevent span.

        Unless the user request with param 'magic' = 'new'
        """
        params = params.copy()
        magic = params.pop('magic', None)

        if magic == 'new':
            return None

        request_hash = hash(json.dumps(params, sort_keys=True))
        last_request_hash = self.session.setdefault('last_request', request_hash)
        last_machine_magic = self.session.get('last_machine_magic')

        if request_hash == last_request_hash and last_machine_magic:
            machines = await Machine.find_all({
                'magic': last_machine_magic
            })
            if machines:
                return machines

        return None

    pre_request = pre_query

    async def pre_provision(self, machine: Machine, query: dict):
        """
        Before provision, checking if provision is allowed and if allowed
        remember the current provision parameters (use hash).
        """
        magic = machine['magic'] = machine['magic'] or random_key()
        self.session['last_machine_magic'] = magic

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
        request['magic'] = await Magic(request)
    return magic_handler