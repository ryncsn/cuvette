"""
Inspect a machine's CPU
"""
from cuvette.inspectors.base import InspectorBase, flat_match, flat_filter
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

    @classmethod
    async def inspect(cls, machine: Machine, conn):
        # TODO
        if 'disk-total_size' not in machine.keys():
            raise Exception()
        if 'disk-number' not in machine.keys():
            raise Exception()

    @classmethod
    def match(cls, query):
        return flat_match(cls, query)

    @classmethod
    def create_filter(cls, query):
        return flat_filter(cls, query)
