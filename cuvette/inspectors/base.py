"""
Base classed and helper for inspectors
"""
import abc
import logging

from cuvette.pool.machine import Machine
from asyncssh.connection import SSHConnection

logger = logging.getLogger(__name__)


class InspectorBase(metaclass=abc.ABCMeta):
    provide = abc.abstractproperty()
    """
    What parameters are provided by this Inspector
    """
    def __init__(self):
        """
        Do some self check or setup code here.
        """
        pass

    @abc.abstractmethod
    async def inspect(self, machine: Machine, conn: SSHConnection):
        """
        Inspact a machine with given ssh connection

        ssh connection is managed outside this function so each
        inspector have their own ssh context for cleaner detection.
        """
        pass

    @abc.abstractmethod
    def match(self, machine: Machine, query: dict):
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

    @abc.abstractmethod
    def hard_filter(self, query: dict):
        """
        Filter out machines by hard limits,

        This should return a mongodb query which filters all machine
        don't meet and CAN'T be transformed to meet the query condition.
        """
        pass

    @abc.abstractmethod
    def soft_filter(self, query: dict):
        """
        Filter out machines by hard limits,

        This should return a mongodb query which filters all machine
        don't meet but CAN be transformed to meet the query condition.
        """
        pass

    @abc.abstractmethod
    def provision_filter(self, query: dict):
        """
        Create a filter that will be acceptaced by provisioners

        Inspectors will do some extra job to preprocess the query for provisioners
        Eg. query contains key 'hugepage' = True, will be turn into a extra cpu flag
        before passing to provisioner.
        """
        pass


def flat_match(self: InspectorBase, machine: Machine, query: dict):
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

    for prop, meta in self.provide.items():
        if prop not in query.keys():
            continue
        if prop not in machine.keys():
            logger.error("Machine don't have prop %s, machine content %s", prop, machine)
            continue

        # op is None for plain value
        for op, value in query[prop].items()\
                if isinstance(query[prop], dict) else {None: query[prop]}:
            # Use default op specified by inspector (or 'eq') if None is given
            op = op or meta.get('default_op', 'eq')

            if OPERATE_MAP.get(op) is None:
                logger.error('Unknown operation: "%s"', query[prop][0])
            elif OPERATE_MAP.get(op)(machine['prop'], query[prop][1]) is False:
                return False

    return True


def flat_filter(self: InspectorBase, query: dict):
    """
    Flat filter, this could be used as a helper.
    Just passthrough the filter.
    """
    ret = {}

    # TODO: op, default_op, default_value

    for prop, meta in self.provide.items():
        if prop not in query.keys():
            # TODO: default value?
            continue

        if isinstance(query[prop], dict):
            ret[prop] = query[prop]

        op = meta.get('default_op', None)
        if op:
            ret[prop] = {op: query[prop]}
        else:
            ret[prop] = query[prop]

    return ret
