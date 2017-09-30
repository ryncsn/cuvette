"""
Inspectors
"""
import logging
import asyncssh

from cuvette.utils import find_all_sub_module, load_all_sub_module
from cuvette.pool import failure_pool
from cuvette.pool.machine import Machine

logger = logging.getLogger(__name__)

__all__ = find_all_sub_module(__file__, exclude=['base'])
Inspectors = dict((k, v.Inspector()) for k, v in load_all_sub_module(__name__).items())


def get_all_parameters():
    """
    Return a dictionary descripting the parameters provided by all inspectors
    """
    ret = {}
    for inspctor in Inspectors.values():
        for key, value in inspctor.provide.items():
            if key in ret.keys():
                logger.warn('Found duplicated parameter %s', key)
            ret[key] = value
    return ret


Parameters = get_all_parameters()


async def perform_check(machine: Machine):
    try:
        async with asyncssh.connect(machine['hostname'],
                                    known_hosts=None,
                                    username='root') as conn:
            # TODO: Disabled host key checking
            # TODO: Accept password
            # TODO: Accept username
            for ins in Inspectors.values():
                await ins.inspect(machine, conn)
    except (OSError, asyncssh.Error) as error:
        logger.exception('Failed inspecting machine %s with exception:', machine)
        machine.move(failure_pool)
