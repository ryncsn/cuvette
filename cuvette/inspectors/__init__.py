"""
Inspectors
"""
import logging
import asyncssh
from cuvette.utils import find_all_sub_module, load_all_sub_module
from cuvette.machine import Machine, failure_pool

__all__ = find_all_sub_module(__file__, exclude=['base'])
Inspectors = dict((k, v.Inspector) for k, v in load_all_sub_module(__name__).items())


async def perform_check(machine: Machine):
    try:
        with asyncssh.connect(machine['hostname']) as conn:
            for ins in Inspectors:
                ins.inspect(machine, conn)
    except (OSError, asyncssh.Error) as error:
        logging.exception('Failed inspecting machine %s with exception:', machine)
        machine.move(failure_pool)
