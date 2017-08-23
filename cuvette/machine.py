"""
Module to manage a beaker machine

Use MongoDB collection as the main machine ppol,
every machine object stored in it is "in the pool"
"""
from datetime import datetime
from motor import motor_asyncio
from motor.motor_asyncio import AsyncIOMotorCollection

client = motor_asyncio.AsyncIOMotorClient()  # XXX

db = client['testdatabase']  # XXX

# Currently only one pool
main_pool = db.machines
provision_pool = db.provisioning_machines
transform_pool = db.transforming_machines
reserved_pool = db.reserved_machines
failure_pool = db.failed_machines


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
        self['tasks'] = {}
        self.update(kwargs)

        self._connection = None

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

    @classmethod
    def load(cls, res):
        """
        Load from a object, like db result
        """
        machine = cls()
        machine.update(res)
        return machine

    async def save(self, pool: AsyncIOMotorCollection):
        """
        Save this machine to a pool
        """
        if pool is main_pool or pool is transform_pool:
            assert self['hostname']
        await pool.insert_one(self)
        self.update(await pool.find_one(self._ident()))

    async def delete(self):
        """
        Delete this machine from all pools
        """
        await main_pool.delete_one(self._ident())
        await provision_pool.delete_one(self._ident())
        await transform_pool.delete_one(self._ident())
        await failure_pool.delete_one(self._ident())

    async def move(self, pool: AsyncIOMotorCollection):
        """
        Move this machine to a pool
        """
        await self.delete()
        await self.save(pool)
