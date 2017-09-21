"""
Inspect a machine's CPU
"""
import logging

from datetime import datetime
from datetime import timedelta
from cuvette.inspectors.base import InspectorBase, flat_match, flat_filter
from cuvette.pool.machine import Machine

MAX_LIFESPAN = 1209600


class Inspector(InspectorBase):
    """
    Inspect machine's CPU
    """
    provide = {
        "system-type": {
            "type": str,
            "description": "Machine type, usually baremetal, vm or maybe container?"
        },
        "hostname": {
            "type": str,
            "description": "A hostname which could be used for ssh connect"
        },
        "lifespan": {
            "type": int,
            "default_op": "$gte",
            "description": "How long this machine will be avaliable"
        },
        "start_time": {
            "type": datetime,
            "description": (
                "When did the machine provisioned, used together with lifespan"
                "to determine if it's expired or not"
            )
        },
        "expire_time": {
            "type": datetime,
            "description": (
                "When this machine will be expired"
            )
        },
        "lifetime": {
            "type": int,
            "description": "How lone a machine will be avaliable from now on, time in seconds"
        },
    }

    @classmethod
    async def inspect(cls, machine: Machine, conn):
        """
        This inspector won't detect anything as all properties should be provide by provisioner
        Else we have a broken provisioner.
        """
        res = await conn.run('cat /proc/cpuinfo')

        res_dict = dict([
            (k.strip(), v.strip()) for k, v in
            [line.split(':', 1) for line in res.stdout.splitlines()]])

        if 'hypervisor' in res_dict.get('flags', ''):
            if machine.setdefault('system-type', 'vm') == 'baremetal':
                logging.error('Machine %s seems to be an virtual machine but provisioner marked it as '
                              'baremetal!', machine['hostname'])

        if 'expire_time' not in machine.keys():
            start_time = machine['start_time']
            lifespan = machine['lifespan']
            machine['expire_time'] = start_time + timedelta(seconds=lifespan)
        for prop in cls.provide.keys():
            if prop in ['lifetime']:
                continue
            if machine.get(prop) is None:
                logging.error("Illegal machine object found, missing prop '%s', content '%s'", prop, machine)

    @classmethod
    def match(cls, query):
        return flat_match(cls, query)

    @classmethod
    def create_filter(cls, query: dict):
        ret = flat_filter(cls, query)
        if 'lifetime' in query.keys():
            del ret['lifetime']
            ret['expire_time'] = {
                '$gte': datetime.now() + timedelta(seconds=int(query['lifetime']))
            }
        return ret
