"""
Async Executor for tasks.

Some jobs are synchronous, let them run in executor
"""
import logging
from cuvette.inspectors import perform_check
from cuvette.tasks import BaseTask

logger = logging.getLogger(__name__)


class InspectTask(BaseTask):
    """
    The helper task to teardown a machine
    """
    TYPE = 'inspect'

    def __init__(self, machines, *args, **kwargs):
        super(InspectTask, self).__init__(machines, *args, **kwargs)

    async def routine(self):
        for machine in self.machines:
            await perform_check(machine)
