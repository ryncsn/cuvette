"""
Inspect a machine's CPU
"""
from cuvette.inspectors.base import InspectorBase, flat_match, flat_filter
from cuvette.pool.machine import Machine


class Inspector(InspectorBase):
    """
    Inspect machine's CPU
    """
    provide = {
        "memory-total_size": {
            "type": int,
            "description": "Memory size in MB"
        },
    }

    @classmethod
    async def inspect(cls, machine: Machine, conn):
        pass

    @classmethod
    def match(cls, query):
        return flat_match(cls, query)

    @classmethod
    def create_filter(cls, query):
        return flat_filter(cls, query)
