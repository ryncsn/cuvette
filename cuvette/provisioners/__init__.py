"""
Provisoiners
"""
import logging

from cuvette.utils import find_all_sub_module, load_all_sub_module
from .base import sanitize_query, ValidateError  # noqa

logger = logging.getLogger(__name__)

__all__ = find_all_sub_module(__file__, exclude=['base'])
Provisioners = dict((k, v.Provisioner()) for k, v in load_all_sub_module(__name__).items())

__all__.extend(['ValidateError'])


def get_all_parameters():
    """
    Return a dictionary descripting the parameters provided by all inspectors
    """
    ret = {}
    for provisioner in Provisioners.values():
        for key, value in provisioner.accept.items():
            ret[key] = value
    return ret


Parameters = get_all_parameters()


def find_avaliable(query):
    min_cost, min_cost_provisioner = float('inf'), None
    for provisioner in Provisioners.values():
        query = sanitize_query(query, provisioner.accept)
        if provisioner.avaliable(query):
            if provisioner.cost(query) < min_cost:
                min_cost_provisioner = provisioner

    return min_cost_provisioner
