"""
Module to manage a beaker machine

Use MongoDB collection as the main machine pool,
every machine object stored in it is "in the pool"
"""
import uuid
import logging

from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection

from cuvette.mongodb import get_machine_collection
from pymongo.collection import ReturnDocument

logger = logging.getLogger(__name__)


class UpdateDict(dict):
    """
    Like a dict, but record the modification
    """
    def __init__(self, *args, **kwargs):
        super(UpdateDict, self).__init__(*args, **kwargs)
        self.__updates__ = []

    def __setitem__(self, item, value):
        if item not in self.keys():
            self.__updates__.append(('update', item, value))

    def __delitem__(self, item):
        self.__updates__.append(('delete', item, None))

    def clean_update_history(self):
        self.__updates__ = []


class Machine(UpdateDict):
    """
    A pure machine model with no logic binded

    Only support one layer of update detect, any update of nested object will
    be treated as replacement.

    Operate like a dict and call save() for bulk operation
    Use .set() and .inc(), .dec() etc for atomic operation
    """

    @classmethod
    async def find_all(cls, db, query={}, count=None, pool=None, **kwargs):
        """
        We are likely to have a upbound of less than 1000 machines,
        so returning a list is fine for performance.
        """
        pool = pool or get_machine_collection(db)
        return [
            cls(db, machine) for machine in await pool.find(query, **kwargs).to_list(count)]

    @classmethod
    async def find_one(cls, db, query={}, pool=None, **kwargs):
        pool = pool or get_machine_collection(db)
        return cls(db, await pool.find_one(query, **kwargs))

    @classmethod
    async def create_one(cls, db, query={}, pool=None, **kwargs):
        return cls(db, await pool.find_one(query, **kwargs))

    def __init__(self, db, *args, **kwargs):
        """
        Initialize a new machine dictionary with:
        machine(<dict>)

        Or:
        machine(hostname='example.com', provisioner='provisioner-example', ...)

        Hostname and magic is always required,
        even if they could be empty at early stage of provisioning
        """
        super(Machine, self).__init__(*args, **kwargs)
        self.setdefault('magic', str(uuid.uuid1()))
        self.setdefault('status', 'new')
        self.setdefault('tasks', {})
        self.setdefault('meta', {})
        self.update(kwargs)

        self.db = db

    def __setitem__(self, item, value):
        dict.__setitem__(self, item, value)

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
        if not self['magic']:
            raise RuntimeError('Invalid machine object without magic')
        if not self['status'] in {'new', 'preparing', 'reserved', 'teardown', 'ready', 'failed', 'deleted'}:
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

    async def inc(self, key, value=1):
        ret = await get_machine_collection(self.db).find_one_and_update(self._ident(), {
            '$inc': {
                key: value
            }
        }, return_document=ReturnDocument.AFTER)
        if ret:
            self.update(ret)
        else:
            raise RuntimeError("Machine {} was deleted while accessing".format(self))

    async def dec(self, key, value=1):
        ret = await get_machine_collection(self.db).find_one_and_update(self._ident(), {
            '$inc': {
                key: -value
            }
        }, return_document=ReturnDocument.AFTER)
        if ret:
            self.update(ret)
        else:
            raise RuntimeError("Machine {} was deleted while accessing".format(self))

    async def set(self, update, value=None):
        """
        For nested object use "."
        eg. set("meta.beaker-pull_count", 0)
        """
        if isinstance(update, dict) and value is None:
            ret = await get_machine_collection(self.db).find_one_and_update(self._ident(), {
                '$set': update
            }, return_document=ReturnDocument.AFTER)
        else:
            ret = await get_machine_collection(self.db).find_one_and_update(self._ident(), {
                '$set': {
                    update: value
                }
            }, return_document=ReturnDocument.AFTER)
        if ret:
            self.update(ret)
        else:
            raise RuntimeError("Machine {} was deleted while accessing".format(self))

    async def unset(self, key):
        """
        For nested object use "."
        eg. unset("meta.beaker-pull_count")
        """
        if isinstance(key, list):
            keys = key
            ret = await get_machine_collection(self.db).find_one_and_update(
                self._ident(), {
                    "$unset": dict([(key, "") for key in keys])
                },
                return_document=ReturnDocument.AFTER
            )
        else:
            ret = await get_machine_collection(self.db).find_one_and_update(
                self._ident(), {
                    "$unset": {
                        key: ""
                    }
                },
                return_document=ReturnDocument.AFTER
            )
        if ret:
            self.update(ret)
        else:
            raise RuntimeError("Machine {} was deleted while accessing".format(self))

    async def refresh(self):
        machine = await get_machine_collection(self.db).find_one(self._ident())
        if not machine:
            raise RuntimeError("Machine %s is deleted while some coroutine still attached" % self)
        self.update(machine)

    async def save(self):
        """
        Save this machine to a pool
        """
        self.self_check()
        if self.get('_id', None) is None:
            self['_id'] = (await get_machine_collection(self.db)
                           .insert_one(self)).inserted_id
            self.clean_update_history()
        else:
            delete = set()
            update = {}
            for op, key, value in self.__updates__:
                if op == 'update':
                    if key in delete:
                        delete.remove(key)
                    update[key] = value
                elif op == 'delete':
                    if key in update:
                        del update[key]
                    else:
                        delete.add(key)
            query = {}
            if update:
                query['$set'] = update
            if delete:
                query['$unset'] = list(delete)
            if query:
                await get_machine_collection(self.db).find_one_and_update(
                    self._ident(),
                    query
                )
            self.clean_update_history()

    async def delete(self):
        """
        Delete this machine from all pools
        """
        self['status'] = 'deleted'
        self.clean_update_history()
        await get_machine_collection(self.db).delete_one(self._ident())

    async def fail(self, message=None):
        """
        Mark this machine as failed
        """
        self['status'] = 'failed'
        if message:
            self['failure-message'] = message
        await self.save()
