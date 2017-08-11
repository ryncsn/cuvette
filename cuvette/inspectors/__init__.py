"""
Plugin loader
"""
import abc
import logging

from asyncssh.connection import SSHConnection

from cuvette.utils import find_all_sub_module
from cuvette.machine import Machine

__all__ = find_all_sub_module(__file__)


class InspectorBase(metaclass=abc.ABCMeta):
    provide = abc.abstractproperty()

    @abc.abstractmethod
    async def inspect(machine: Machine, conn: SSHConnection):
        """
        Inspact a machine with given ssh connection

        ssh connection is managed outside this function so each
        inspector have their own ssh context for cleaner detection.
        """
        pass

    @abc.abstractmethod
    def match(machine: Machine, query: dict):
        """
        Judge if one machine matches the query.

        The query passed in is a mongodb like query:
        {
            "magic": 1,
            "cpu.num": {
                '$gt': 1,
                '$lte': 4,
            },
            "cpu.num": {
                '$in': [41, 42, 43],
            },
            ...
        }

        Use flat_match for built-in native python type compare.

        This function should return immediately, and it should be considered
        an error if any machine prop is absent, cause inspect() is async and
        time comsuming, but match should alway return immediately, inspect()
        should always be called before match().

        # TODO
        For better performance, use create_filter to create a filter to make use
        of MongoDB's index. We keep the query mongodb style to make it easier to
        pass it to mongodb.
        """
        pass

#     @abc.abstractmethod
#     def create_filter(query: dict):
#         """
#         """
#         pass
#
#
# def flat_filter(query: dict):
#     """
#     """
#     return query


def flat_match(cls: InspectorBase, machine: Machine, params: dict):
    """
    Flat compare, this could be used as a helper.
    """
    OPERATE_MAP = {
        '$eq': lambda x, val: x == val,
        '$in': lambda x, val: x in val,
        '$lt': lambda x, val: x < val,
        '$lte': lambda x, val: x <= val,
        '$gt': lambda x, val: x > val,
        '$gte': lambda x, val: x >= val,
    }

    for prop, meta in cls.provide.items():
        if prop not in params.keys():
            continue
        if prop not in machine.keys():
            logging.error("Machine don't have prop %s, machine content %s", prop, machine)
            continue

        # op is None for plain value
        for op, value in params[prop].items()\
                if isinstance(params[prop], dict) else {None: params[prop]}:
            # Use default op specified by inspector (or 'eq') if None is given
            op = op or meta.get('default_op', 'eq')

            if OPERATE_MAP.get(op) is None:
                logging.error('Unknown operation: "%s"', params[prop][0])
            elif OPERATE_MAP.get(op)(machine['prop'], params[prop][1]) is False:
                return False

    return True
