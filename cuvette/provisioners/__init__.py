"""
Provisoiners
"""
from cuvette.utils import find_all_sub_module, load_all_sub_module
from .base import sanitize_query

__all__ = find_all_sub_module(__file__, exclude=['base'])
Provisioners = dict((k, v.Provisioner) for k, v in load_all_sub_module(__name__).items())


def find_avaliable(query):
    min_cost, min_cost_provisioner = float('inf'), None
    for provisioner in Provisioners.values():
        query = sanitize_query(query, provisioner.accept)
        if provisioner.avaliable(query):
            if provisioner.cost(query) < min_cost:
                min_cost_provisioner = provisioner

    return min_cost_provisioner
