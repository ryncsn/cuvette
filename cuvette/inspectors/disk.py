"""
Inspect a machine's CPU
"""
from cuvette.inspectors.base import InspectorBase


class Inspector(InspectorBase):
    """
    Inspect machine's Disk
    """
    PARAMETERS = {
        "disk-total_size": {
            "type": int,
            "description": "Disk total size in MB"
        },
        "disk-number": {
            "type": int,
            "description": "Physical disk number"
        },
    }

    async def inspect(cls, machine, conn):
        # TODO
        if 'disk-total_size' not in machine.keys():
            raise Exception()
        if 'disk-number' not in machine.keys():
            raise Exception()
