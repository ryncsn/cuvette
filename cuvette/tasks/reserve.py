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
    The helper task to teardown a machine
    """
    TYPE = 'reserve'

    def __init__(self, machines: typing.List[Machine], reserve_time, *args, **kwargs):
        self.reserve_time = reserve_time
        super(ReserveTask, self).__init__(machines, *args, **kwargs)

    async def on_success(self):
        for machine in self.machines:
            await perform_check(machine)

    async def routine(self):
        await asyncio.sleep(self.reserve_time)
