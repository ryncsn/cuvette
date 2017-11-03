"""
Inspect a machine's CPU
"""
import logging

from cuvette.inspectors.base import InspectorBase

logger = logging.getLogger(__name__)


class Inspector(InspectorBase):
    """
    Inspect machine's CPU
    """
    PARAMETERS = {
        "whiteboard": {
            "description": "Additional string info for each machine.",
            "type": str,
        },
    }

    async def inspect(self: InspectorBase, machine, conn):
        """
        Do nothing
        """
        machine.setdefault('whiteboard', '')

    def hard_filter(self, query: dict):
        """
        Filter nothing
        """
        return {}

    soft_filter = hard_filter
