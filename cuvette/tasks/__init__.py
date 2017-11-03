"""
Provisoiners
"""
import logging

from cuvette.tasks.base import BaseTask, Tasks
from .provision import ProvisionTask
from .inspect import InspectTask
from .reserve import ReserveTask
from .teardown import TeardownTask

logger = logging.getLogger(__name__)

__all__ = ['BaseTask', 'ProvisionTask', 'InspectTask', 'ReserveTask', 'TeardownTask', 'Tasks']


async def retrive_tasks_from_machine(machine):
    """
    Retrive cuvette tasks on a machine
    """
    ret = []
    dropped = False
    for task_uuid in list(machine['tasks'].keys()).copy():
        task = Tasks.get(task_uuid)  # TODO, remove singleton
        if not task:
            logger.error('Dropped dead task: {}'.format(task_uuid))
            machine['tasks'].pop(task_uuid)
            dropped = True
        else:
            ret.append(task)
    if dropped:
        await machine.save()
    return ret
