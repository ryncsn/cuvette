"""
Inspect a machine's CPU
"""
from cuvette.inspectors.base import InspectorBase, flat_match, flat_filter
from cuvette.pool.machine import Machine


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
    provide = {
        "cpu-arch": {
            "type": str,
            "description": ""
        },
        "cpu-vendor": {
            "type": str,
            "description": "CPU Vendor, Intel, AMD, etc."
        },
        "cpu-model": {
            "type": str,
            "description": "CPU model, code name like sandybridge, westmer, or ID in integer"
        }
    }

    @classmethod
    async def inspect(cls, machine: Machine, conn):
        res = await conn.run('lscpu')
        res_dict = dict([
            (k.strip(), v.strip()) for k, v in
            [line.split(':', 1) for line in res.stdout.splitlines()]])
        print(res_dict)

        machine['cpu-arch'] = res_dict['Architecture']
        machine['cpu-vendor'] = res_dict['Vendor ID']
        machine['cpu-model'] = res_dict['Model']

    @classmethod
    def match(cls, query):
        return flat_match(cls, query)

    @classmethod
    def create_filter(cls, query):
        return flat_filter(cls, query)
