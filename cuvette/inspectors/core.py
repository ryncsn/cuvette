"""
Inspect a machine's CPU
"""
import logging

from datetime import datetime
from cuvette.inspectors.base import InspectorBase, flat_match, flat_filter
from cuvette.machine import Machine


class Inspector(InspectorBase):
    """
    Inspect machine's CPU
    """
    provide = {
        "type": {
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
        "start_at": {
            "type": datetime,
            "description": (
                "When did the machine provisioned, used together with lifespan"
                "to determine if it's expired or not"
            )
        },
    }

    @classmethod
    async def inspect(cls, machine: Machine, conn):
        """
        This inspector won't detect anything as all properties should be provide by provisioner
        Else we have a broken provisioner.
        """
        for prop in cls.provide.keys():
            if machine.get(prop) is None:
                logging.error("Illegal machine object found, missing prop '%s', content '%s'", prop, machine)

    @classmethod
    def match(cls, query):
        return flat_match(cls, query)

    @classmethod
    def create_filter(cls, query):
        return flat_filter(cls, query)
