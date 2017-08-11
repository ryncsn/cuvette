"""
Module to manage a beaker machine

Use MongoDB collection as the main machine ppol,
every machine object stored in it is "in the pool"
"""
from datetime import datetime
from motor import motor_asyncio

client = motor_asyncio.AsyncIOMotorClient()

db = client['testdatabase']  # XXX

# Currently only one pool
main_pool = db.machines


class Machine(dict):
    """
    A pure machine model with no logic binded
    """
    @staticmethod
    def all(**kwargs):
        return main_pool.find(**kwargs)

    @classmethod
    async def get_all(cls, **kwargs):
        return [
            cls(machine) for machine in await cls.all(**kwargs).to_list()]

    @staticmethod
    async def setup(*_, **kwargs):
        return main_pool.create_index("hostname", unique=True)

    def __init__(self,
                 hostname: str = None,
                 magic: str = None,
                 provisioner: str = None,
                 start_time: datetime = None,
                 lifespan: int = 0,
                 **kwargs):
        """
        Hostname and magic is always required,
        even if they could be empty at early stage of provisioning
        """
        self['magic'] = magic
        self['hostname'] = hostname
        self['provisioner'] = provisioner
        self['start_time'] = start_time
        self['lifespan'] = lifespan

        # Right now Tasks could could only be an instance of
        # Provision / Transform / Reserve
        self['tasks'] = []
        self.update(kwargs)

        self._connection = None

    def _ident(self):
        """
        Filter used to get this object from mongodb pool
        """
        return {'hostname': self['hostname']}

    async def save(self):
        """
        Filter used to get this object from mongodb pool
        """
        # Hostname is always required before save to pool
        if await main_pool.update_one(self._ident(), self):
            return self
        await main_pool.insert_one(self)
        self.update(await main_pool.find_one(self._ident()))
