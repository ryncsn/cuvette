"""
Async Executor for tasks.

Some jobs are synchronous, let them run in executor
"""
import logging
import asyncio
import typing

from cuvette.tasks import BaseTask
from cuvette.pool.machine import Machine
from cuvette.inspectors import perform_check

logger = logging.getLogger(__name__)


class ReserveTask(BaseTask):
    """
    The revervation task, wait for given time then the task is done
    """
    TYPE = 'reserve'

    def __init__(self, machines: typing.List[Machine], reserve_time, *args, **kwargs):
        super(ReserveTask, self).__init__(machines, *args, **kwargs)
        self.reserve_time = reserve_time
        self.meta['reserve_time'] = reserve_time

    async def on_success(self):
        for machine in self.machines:
            await perform_check(machine)
            machine['status'] = 'ready'
        await super(ReserveTask, self).on_success()

    async def routine(self):
        for machine in self.machines:
            machine['status'] = 'reserved'
            await machine.save()
        try:
            await asyncio.sleep(self.reserve_time)
        except Exception as error:
            # Most likely cancelled
            logger.exception(error)