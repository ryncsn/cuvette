"""
Provisoiners
"""
import logging

from cuvette.utils import find_all_sub_module, load_all_sub_module, sanitize_query
from cuvette.utils.parameters import get_all_parameters

logger = logging.getLogger(__name__)

__all__ = find_all_sub_module(__file__, exclude=['base'])

Provisioners = dict((k, v.Provisioner()) for k, v in load_all_sub_module(__name__).items())


Parameters = get_all_parameters(Provisioners.values(),
                                'provisoiner',
                                name_getter=lambda module: module.NAME,
                                exclude_keys=['description'])
Parameters.update({
    'provision-count': {
        'type': int,
        'ops': [None],
        'default': lambda query: query.get('count') or 1
    },
    'provision-lifespan': {
        'type': int,
        'ops': [None],
        'default': lambda query: max(int(query.get('lifespan') or query.get('lifetime') or 0), 86400) * 2
    }
})


def find_avaliable(query):
    min_cost, min_cost_provisioner = float('inf'), None
    for provisioner in Provisioners.values():
        query = sanitize_query(query, provisioner.PARAMETERS)
        if provisioner.avaliable(query):
            if provisioner.cost(query) < min_cost:
                min_cost_provisioner = provisioner

    return min_cost_provisioner
