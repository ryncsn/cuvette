"""
Provisoiners
"""
import logging
import asyncio

from cuvette.tasks.base import BaseTask, Tasks
from cuvette.utils.parameters import get_all_parameters
from .provision import ProvisionTask
from .inspect import InspectTask
from .reserve import ReserveTask
from .teardown import TeardownTask

logger = logging.getLogger(__name__)

__all__ = ['BaseTask', 'ProvisionTask', 'InspectTask', 'ReserveTask', 'TeardownTask', 'Tasks', 'resume_task']


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


async def resume_task(task_uuid, task_type, task_query, machines):
    for task in [ProvisionTask, InspectTask, ReserveTask, TeardownTask]:
        if task.TYPE == task_type:
            print("Provingingingignini")
            task = await task.resume(task_uuid, task_query, machines)
            await asyncio.wait([task.run()], timeout=0)
            return
    logger.error("Unknown task type: %s: %s", task_type, task_uuid)


Parameters = get_all_parameters(
    [ProvisionTask, InspectTask, ReserveTask, TeardownTask], 'task',
    name_getter=lambda task: str(task)
)
