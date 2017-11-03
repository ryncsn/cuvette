"""
Inspect a machine's CPU
"""
import logging

from cuvette.inspectors.base import InspectorBase
from cuvette.inspectors.base import flat_filter

logger = logging.getLogger(__name__)


class Inspector(InspectorBase):
    """
    Inspect machine's CPU
    """
    PARAMETERS = {
        "tags": {
            "description": "Tag the machine for better managing.",
            "type": list,
        },
    }

    async def inspect(self: InspectorBase, machine, conn):
        """
        Do nothing
        """
        machine.setdefault('tags', [])

    hard_filter = flat_filter

    soft_filter = hard_filter
