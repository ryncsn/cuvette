"""
Provisoiners
"""
import logging
from cuvette.utils import find_all_sub_module, load_all_sub_module
from cuvette.inspectors import Parameters as InspectorParameters
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


def check_parameters():
    """
    Check if parameters accept by provisioners are valid for inspectors
    """
    for provisioner in Provisioners.values():
        for param_name, param_meta in provisioner.accept.items():
            inspected_param_meta = InspectorParameters.get(param_name)
            if not inspected_param_meta:
                logging.error('Parameter "%s" of provisioner "%s" is not inspected by any inspector',
                              param_name, provisioner.name)


check_parameters()
