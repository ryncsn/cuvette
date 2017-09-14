"""
Base classed and helper for inspectors
"""
import abc
import logging

from cuvette.pool.machine import Machine
from asyncssh.connection import SSHConnection


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

    @abc.abstractmethod
    def create_filter(query: dict):
        pass


def flat_match(cls: InspectorBase, machine: Machine, query: dict):
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
        if prop not in query.keys():
            continue
        if prop not in machine.keys():
            logging.error("Machine don't have prop %s, machine content %s", prop, machine)
            continue

        # op is None for plain value
        for op, value in query[prop].items()\
                if isinstance(query[prop], dict) else {None: query[prop]}:
            # Use default op specified by inspector (or 'eq') if None is given
            op = op or meta.get('default_op', 'eq')

            if OPERATE_MAP.get(op) is None:
                logging.error('Unknown operation: "%s"', query[prop][0])
            elif OPERATE_MAP.get(op)(machine['prop'], query[prop][1]) is False:
                return False

    return True


def flat_filter(cls: InspectorBase, query: dict):
    """
    Flat filter, this could be used as a helper.
    Just passthrough the filter.
    """
    ret = {}

    for prop, meta in cls.provide.items():
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
