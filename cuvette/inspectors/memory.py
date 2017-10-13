"""
Inspect a machine's CPU
"""
from cuvette.inspectors.base import InspectorBase


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

    async def inspect(cls, machine, conn):
        pass
