"""
Inspect a machine's CPU
"""
import logging

from datetime import datetime
from datetime import timedelta
from cuvette.inspectors.base import InspectorBase, flat_filter

MAX_LIFESPAN = 1209600


logger = logging.getLogger(__name__)


class Inspector(InspectorBase):
    """
    Inspect machine's CPU
    """
    PARAMETERS = {
        "magic": {
            "description": "A surrogate key for each machine, could be a reserved keyword, currently "
            "reserved keywords are 'noprovision', 'new'",
        },
        "status": {
            "type": str,
            "description": "Machine status, when requesting a machine, this should be 'ready'",
        },
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

    async def inspect(self: InspectorBase, machine, conn):
        """
        This inspector won't detect anything as all properties should be provide by provisioner
        Else we have a broken provisioner.
        """
        res = await conn.run('cat /proc/cpuinfo')
        res_dict = {}
        for line in res.stdout.splitlines():
            try:
                key, value = line.split(':', 1)
            except Exception:
                logger.error("Unexpected line %s", line)
            res_dict[key.strip()] = value.strip()

        if 'hypervisor' in res_dict.get('flags', ''):
            if machine.setdefault('system-type', 'vm') == 'baremetal':
                logger.error('Machine %s seems to be an virtual machine but provisioner marked it as '
                             'baremetal!', machine['hostname'])

        if 'expire_time' not in machine.keys():
            start_time = machine['start_time']
            lifespan = machine['lifespan']
            machine['expire_time'] = start_time + timedelta(seconds=lifespan)
        for prop in self.PARAMETERS.keys():
            if prop in ['lifetime']:
                continue
            if machine.get(prop) is None:
                logger.error("Illegal machine object found, missing prop '%s', content '%s'", prop, machine)

    def hard_filter(self, query: dict):
        ret = flat_filter(self, query)
        if 'lifetime' in query.keys():
            ret.pop('lifetime', None)
            ret['expire_time'] = {
                '$gte': datetime.now() + timedelta(seconds=int(query['lifetime']))
            }
        return ret
