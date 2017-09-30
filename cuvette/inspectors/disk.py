"""
Inspect a machine's CPU
"""
from cuvette.inspectors.base import InspectorBase
from cuvette.pool.machine import Machine


class Inspector(InspectorBase):
    """
    Inspect machine's Disk
    """
    provide = {
        "disk-total_size": {
            "type": int,
            "description": "Disk total size in MB"
        },
        "disk-number": {
            "type": int,
            "description": "Physical disk number"
        },
    }

    async def inspect(cls, machine: Machine, conn):
        # TODO
        if 'disk-total_size' not in machine.keys():
            raise Exception()
        if 'disk-number' not in machine.keys():
            raise Exception()
