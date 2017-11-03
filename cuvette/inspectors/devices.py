"""
Inspect a machine's CPU
"""
from cuvette.inspectors.base import InspectorBase


class Inspector(InspectorBase):
    """
    Inspect machine's CPU
    """
    PARAMETERS = {
        "device_drivers": {
            "type": list,
            "description": "Devices a machine must have",
        }
    }
