"""
Module to manage a beaker machine

Use MongoDB collection as the main machine pool,
every machine object stored in it is "in the pool"
"""
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection

from cuvette.pool import main_pool, failure_pool


class Machine(dict):
    """
    A pure machine model with no logic binded
    """

    @classmethod
    async def find_all(cls, query={}, pool=None, **kwargs):
        """
        We are likely to have a upbound of less than 1000 machines,
        so returning a list is fine for performance.
        """
        pool = pool or main_pool
        return [
            cls(machine) for machine in await pool.find(query, **kwargs).to_list(None)]

    @classmethod
    async def find_one(cls, query={}, pool=None, **kwargs):
        pool = pool or main_pool
        return cls(await pool.find_one(query, **kwargs))

    @staticmethod
    async def setup(*_, **kwargs):
        return main_pool.create_index("hostname", unique=True)

    @property
    def meta(self):
        return self['meta']

    def __init__(self, *args,
                 hostname: str = None,
                 magic: str = None,
                 provisioner: str = None,
                 start_time: datetime = None,
                 lifespan: int = 0,
                 **kwargs):
        """
        Initialize a machine dictionary with:
        machine(<dict>)

        Or:
        machine(hostname='example.com', provisioner='provisioner-example', ...)

        Hostname and magic is always required,
        even if they could be empty at early stage of provisioning
        """
        if args:
            dict.__init__(self, *args)

        self.setdefault('magic', magic)
        self.setdefault('status', 'new')
        self.setdefault('hostname', hostname)
        self.setdefault('provisioner', provisioner)
        self.setdefault('start_time', start_time)
        self.setdefault('lifespan', lifespan)

        # Right now Tasks could could only be an instance of
        # Provision / Transform / Reserve
        self.setdefault('tasks', {})
        self.setdefault('meta', {})

        self.update(kwargs)

        self._connection = None

    def __setitem__(self, item, value):
        dict.__setitem__(self, item, value)
        self.self_check()

    def _ident(self):
        """
        Filter used to get this object from mongodb pool
        """
        if self.get('_id'):
            return {'_id': self['_id']}
        elif self.get('magic'):
            return {'magic': self['magic']}
        elif self.get('hostname'):
            return {'hostname': self['hostname']}
        else:
            raise RuntimeError("Invalid machine object {}".format(self))

    def self_check(self):
        if not self['status'] in {'new', 'preparing', 'teardown', 'ready', 'failed', 'deleted'}:
            raise RuntimeError('Invalid machine status {}'.format(self['status']))
        if self['status'] in {'teardown', 'reserved', 'ready', }:
            if not self['hostname']:
                raise RuntimeError('Machine in status {} must have field "hostname"'.format(self['status']))

    def to_json(self):
        ret = {}
        for key, value in self.items():
            if key.startswith('_'):
                continue
            if isinstance(value, datetime):
                ret[key] = value.isoformat()
            else:
                ret[key] = value
        return ret

    async def save(self, pool: AsyncIOMotorCollection = None):
        """
        Save this machine to a pool
        """
        pool = pool or main_pool
        self.self_check()
        await pool.insert_one(self)
        self.update(await pool.find_one(self._ident()))

    async def delete(self):
        """
        Delete this machine from all pools
        """
        self['status'] = 'deleted'
        await main_pool.delete_one(self._ident())
        await failure_pool.delete_one(self._ident())

    async def fail(self):
        """
        Mark this machine as failed
        """
        self['status'] = 'failed'
        await self.delete()
        await self.save(failure_pool)