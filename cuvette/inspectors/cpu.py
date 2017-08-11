"""
Inspect a machine's CPU
"""
from cuvette.inspectors import InspectorBase, flat_match
from cuvette.machine import Machine


VENDOR_ALIAS = [
    ('GenuineIntel', 'intel', )
    ('AMD', )
    ('IBM', )
]


MODEL_ALIAS = [
    ('42', 'sandybridge', )
    ('47', '44', '37', 'westmere', )
]


class Inspector(InspectorBase):
    """
    Inspect machine's CPU
    """
    provide = {
        "cpu.arch": {
            "type": str,
            "description": ""
        },
        "cpu.vendor": {
            "type": str,
            "description": "CPU Vendor, Intel, AMD, etc."
        },
        "cpu.model": {
            "type": str,
            "description": "CPU model, code name like sandybridge, westmer, or ID in integer"
        }
    }

    async def inspect(machine: Machine, conn):
        res = conn.exec('lscpu')
        res_dict = dict([
            (k.strip(), v.strip()) for k, v in
            [line.split(':', 1) for line in res.splitlines()]])

        machine['cpu.arch'] = res_dict['Architecture']
        machine['cpu.vendor'] = res_dict['Vendor ID']
        machine['cpu.models'] = res_dict['42']

    match = flat_match
