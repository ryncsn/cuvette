import json
import uuid

from aiohttp_session import get_session
from cuvette.pool.machine import Machine


def random_key():
    """
    This key will get exposed, so use uuid4 for security reason.
    """
    return str(uuid.uuid4())


class Magic(object):
    """
    One magic object for one request

    Wrap all hack and implicit there there
    """
    def __init__(self, request):
        self.request = request

    async def query(self, params: dict):
        session = await get_session(self.request)

        params = params.copy()
        magic = params.pop('magic', None)
        if magic == 'new':
            return None

        request_hash = hash(json.dumps(params, sort_keys=True))
        last_request_hash = session.setdefault('last_request', request_hash)
        last_machine_magic = session.get('last_machine_magic')

        if request_hash == last_request_hash and last_machine_magic:
            query = {
                'magic': last_machine_magic
            }
            machines = await Machine.find_all(query)
            if machines:
                return machines

        return None

    async def prepare_provision(self, machine: Machine, query: dict):
        """
        Before provision, checking if provision is allowed and if allowed
        remember the current provision parameters (use hash).
        """
        session = await get_session(self.request)

        if query.get('magic') == 'noprovision':
            return None

        magic = machine['magic'] = machine['magic'] or random_key()
        session['last_machine_magic'] = magic
        return magic

    async def create_filter(self, params: dict):
        """
        Filter out machine belone / not belong to a user / only new provision / never new provision / etc
        """
        params = params.copy()
        magic = params.pop('magic', None)
        if magic == 'new':
            return {'_id': 0}
        return {}
