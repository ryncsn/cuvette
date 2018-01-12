"""
Inspect a machine's CPU
"""
from cuvette.inspectors.base import InspectorBase, flat_filter


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
        },
        "cpu-flags": {
            "type": list,
            "description": "CPU flags need to be supported"
        },
        '1g_hugepage': {
            'type': bool,
            "description": "If huge page is needed, if needed, pdpe1gb is appended to cpu-flags"
        },
    }

    async def inspect(self, machine, conn):
        res = await conn.run('lscpu')
        res_dict = dict([
            (k.strip(), v.strip()) for k, v in
            [line.split(':', 1) for line in res.stdout.splitlines()]])

        machine.setdefault('cpu-arch', res_dict.get('Architecture', 'Unknown'))
        machine.setdefault('cpu-vendor', res_dict.get('Vendor ID', 'Unknown'))
        machine.setdefault('cpu-model', res_dict.get('Model', 'Unknown'))

    def hard_filter(self, query):
        if query.get('1g_hugepage'):
            query.setdefault('cpu-flags', []).append('pdpe1gb')
        return flat_filter(self, query)

    def provision_filter(self, query):
        if query.get('1g_hugepage'):
            query.setdefault('cpu-flags', []).append('pdpe1gb')
        return query
