"""
Inspect a machine's CPU
"""
from cuvette.inspectors.base import InspectorBase


VENDOR_ALIAS = [
    ('GenuineIntel', 'intel', ),
    ('AMD', ),
    ('IBM', )
]


MODEL_ALIAS = [
    ('sandybridge', '42', ),
    ('westmere', '47', '44', '37', )
]


class Inspector(InspectorBase):
    """
    Inspect machine's CPU
    """
    PARAMETERS = {
        "numa-node_number": {
            "type": int,
            "description": "How many numa nodes are needed",
            "op": [None]  # TODO: not used yet
        },
    }

    async def inspect(cls, machine, conn):
        pass
